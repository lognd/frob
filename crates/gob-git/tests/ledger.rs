//! Integration tests against temporary repositories built with gix only.

use std::path::Path;
use std::sync::{Arc, Barrier};

use gob_git::{
    ChangeKind, CommitOptions, GitError, RelPath, Repo, StatusKind, StatusOptions, TreeRef,
};

const MAIN: &str = "refs/heads/main";

fn opts() -> CommitOptions {
    CommitOptions {
        cas_retries: 5,
        author: Some(("Test".into(), "test@example.com".into())),
    }
}

fn rp(s: &str) -> RelPath {
    RelPath::new(s).unwrap()
}

fn change(path: &str, body: &str) -> (RelPath, Option<Vec<u8>>) {
    (rp(path), Some(body.as_bytes().to_vec()))
}

/// Init a repo whose HEAD is symbolic to `main`, with one root commit made by `commit_paths`.
fn fixture() -> (tempfile::TempDir, Repo) {
    let dir = tempfile::tempdir().unwrap();
    let repo = Repo::init(dir.path()).unwrap();
    // Point HEAD at main regardless of init.defaultBranch.
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").unwrap();
    set_local_identity(&repo);
    repo.commit_paths(MAIN, &[change("README.md", "hello\n")], "root", &opts())
        .unwrap();
    (dir, repo)
}

/// Give the repository a local committer identity so spawned `git` never reads the host's config.
fn set_local_identity(repo: &Repo) {
    let cfg = repo.git_dir().join("config");
    let mut text = std::fs::read_to_string(&cfg).unwrap();
    text.push_str("[user]\n\tname = Test\n\temail = test@example.com\n");
    std::fs::write(&cfg, text).unwrap();
}

fn commit_count(repo: &Repo, rev: &str) -> usize {
    let mut n = 0;
    let mut cur = Some(repo.rev_parse(rev).unwrap());
    while let Some(id) = cur {
        n += 1;
        cur = repo.rev_parse(&format!("{id}^")).ok();
    }
    n
}

#[test]
fn root_commit_on_missing_ref_and_checkout_sync() {
    let (dir, repo) = fixture();
    assert_eq!(
        std::fs::read_to_string(dir.path().join("README.md")).unwrap(),
        "hello\n"
    );
    assert_eq!(repo.head().unwrap().branch.as_deref(), Some("main"));
    assert!(repo.status(&StatusOptions::default()).unwrap().is_empty());
}

#[test]
fn concurrent_writers_lose_nothing() {
    let (dir, _repo) = fixture();
    let barrier = Arc::new(Barrier::new(2));
    let handles: Vec<_> = ["tickets/a/ticket.md", "tickets/b/ticket.md"]
        .into_iter()
        .map(|p| {
            let (path, barrier) = (dir.path().to_path_buf(), barrier.clone());
            std::thread::spawn(move || {
                let repo = Repo::discover(&path).unwrap();
                barrier.wait();
                // Bare ref write path only: the checked-out sync is exercised elsewhere.
                repo.commit_paths(MAIN, &[change(p, p)], "add", &opts())
                    .unwrap()
            })
        })
        .collect();
    let outcomes: Vec<_> = handles.into_iter().map(|h| h.join().unwrap()).collect();
    let repo = Repo::discover(dir.path()).unwrap();
    for p in ["tickets/a/ticket.md", "tickets/b/ticket.md", "README.md"] {
        assert!(repo.read_blob_at(MAIN, p).unwrap().is_some(), "{p} missing");
    }
    assert_eq!(commit_count(&repo, MAIN), 3);
    // The checked-out index must carry both entries too (no lost index update).
    assert!(repo.status(&StatusOptions::default()).unwrap().is_empty());
    eprintln!(
        "retries: {:?}",
        outcomes.iter().map(|o| o.retries).collect::<Vec<_>>()
    );
}

// frob:ticket 01M43J70477E91BE3ENHQW1D9E
/// Documented guarantee under any scheduling: every writer either wins or reports
/// `CasExhausted`, at least one wins, and the ref holds exactly the winners' commits.
#[test]
fn twenty_four_concurrent_writers_never_lose_an_update() {
    // frob:tests crates/gob-git/src/ledger.rs::Repo.commit_paths
    let (dir, _repo) = fixture();
    let barrier = Arc::new(Barrier::new(24));
    let handles: Vec<_> = (0..24)
        .map(|i| {
            let (path, barrier) = (dir.path().to_path_buf(), barrier.clone());
            std::thread::spawn(move || {
                let repo = Repo::discover(&path).unwrap();
                let p = format!("tickets/w{i}/ticket.md");
                barrier.wait();
                (
                    p.clone(),
                    repo.commit_paths(MAIN, &[change(&p, "x\n")], "add", &opts()),
                )
            })
        })
        .collect();
    let mut winners = Vec::new();
    for h in handles {
        let (p, res) = h.join().unwrap();
        match res {
            Ok(_) => winners.push(p),
            Err(GitError::CasExhausted { attempts, .. }) => assert_eq!(attempts, 6),
            Err(e) => panic!("unexpected {e}"),
        }
    }
    assert!(!winners.is_empty(), "lock-free progress: someone must win");
    let repo = Repo::discover(dir.path()).unwrap();
    assert_eq!(commit_count(&repo, MAIN), 1 + winners.len());
    for p in &winners {
        assert!(repo.read_blob_at(MAIN, p).unwrap().is_some(), "{p} lost");
    }
}

#[test]
fn staged_unrelated_file_is_untouched() {
    let (dir, repo) = fixture();
    // Stage an unrelated file by hand using the index API.
    std::fs::write(dir.path().join("staged.txt"), "wip\n").unwrap();
    stage(&repo, dir.path(), "staged.txt");
    let before = repo.status(&StatusOptions::default()).unwrap();
    assert!(
        before
            .iter()
            .any(|e| e.path == "staged.txt" && e.staged && e.kind == StatusKind::Added)
    );

    let out = repo
        .commit_paths(
            MAIN,
            &[change("tickets/x/ticket.md", "x1\n")],
            "add x",
            &opts(),
        )
        .unwrap();
    assert_eq!(
        std::fs::read_to_string(dir.path().join("tickets/x/ticket.md")).unwrap(),
        "x1\n"
    );
    let repo = Repo::discover(dir.path()).unwrap();
    assert!(
        repo.read_blob_at(MAIN, "staged.txt").unwrap().is_none(),
        "staged file swept in"
    );
    let after = repo.status(&StatusOptions::default()).unwrap();
    assert_eq!(after, before, "only the staged file should remain dirty");
    assert_eq!(repo.head().unwrap().oid, Some(out.oid));
}

fn stage(repo: &Repo, root: &Path, rel: &str) {
    // Test helper: stage via gix index editing so no git binary is needed.
    let gix = gix::open(repo.work_dir().unwrap()).unwrap();
    let bytes = std::fs::read(root.join(rel)).unwrap();
    let id = gix.write_blob(&bytes).unwrap().detach();
    let mut index = gix.open_index().unwrap();
    let md = gix::index::fs::Metadata::from_path_no_follow(&root.join(rel)).unwrap();
    let stat = gix::index::entry::Stat::from_fs(&md).unwrap();
    index.dangerously_push_entry(
        stat,
        id,
        gix::index::entry::Flags::empty(),
        gix::index::entry::Mode::FILE,
        rel.into(),
    );
    index.sort_entries();
    index.remove_tree();
    index.write(gix::index::write::Options::default()).unwrap();
}

#[test]
fn delete_via_none_and_local_edit_refusal() {
    let (dir, repo) = fixture();
    repo.commit_paths(
        MAIN,
        &[change("tickets/t/ticket.md", "t\n")],
        "add t",
        &opts(),
    )
    .unwrap();
    repo.commit_paths(MAIN, &[(rp("tickets/t/ticket.md"), None)], "rm t", &opts())
        .unwrap();
    assert!(
        repo.read_blob_at(MAIN, "tickets/t/ticket.md")
            .unwrap()
            .is_none()
    );
    assert!(!dir.path().join("tickets/t/ticket.md").exists());
    assert!(repo.status(&StatusOptions::default()).unwrap().is_empty());

    // A local edit to a ledger path is refused with a remedy.
    repo.commit_paths(MAIN, &[change("tickets/e.md", "1\n")], "add e", &opts())
        .unwrap();
    std::fs::write(dir.path().join("tickets/e.md"), "mine\n").unwrap();
    let err = repo
        .commit_paths(MAIN, &[change("tickets/e.md", "2\n")], "upd e", &opts())
        .unwrap_err();
    assert!(matches!(err, GitError::LocalEdits { .. }), "{err}");
    assert_eq!(err.code(), "E-GIT-LOCAL-EDITS");
}

#[test]
fn cas_exhausted_when_ref_keeps_churning() {
    let (dir, repo) = fixture();
    let other = Repo::discover(dir.path()).unwrap();
    let mut n = 0;
    let o = CommitOptions {
        cas_retries: 3,
        ..opts()
    };
    let err = repo
        .commit_paths_with(MAIN, &[change("tickets/z.md", "z\n")], "z", &o, &mut |_| {
            n += 1;
            other
                .commit_paths(
                    MAIN,
                    &[change(&format!("churn/{n}.md"), "c\n")],
                    "churn",
                    &opts(),
                )
                .unwrap();
        })
        .unwrap_err();
    match err {
        GitError::CasExhausted { attempts, .. } => assert_eq!(attempts, 4),
        e => panic!("unexpected {e}"),
    }
    assert!(repo.read_blob_at(MAIN, "tickets/z.md").unwrap().is_none());
}

#[test]
fn cas_succeeds_after_one_lost_race() {
    let (dir, repo) = fixture();
    let other = Repo::discover(dir.path()).unwrap();
    let mut first = true;
    let out = repo
        .commit_paths_with(
            MAIN,
            &[change("tickets/y.md", "y\n")],
            "y",
            &opts(),
            &mut |_| {
                if std::mem::take(&mut first) {
                    other
                        .commit_paths(MAIN, &[change("tickets/w.md", "w\n")], "w", &opts())
                        .unwrap();
                }
            },
        )
        .unwrap();
    assert_eq!(out.retries, 1);
    for p in ["tickets/y.md", "tickets/w.md"] {
        assert!(repo.read_blob_at(MAIN, p).unwrap().is_some());
    }
}

#[test]
fn read_apis() {
    let (dir, repo) = fixture();
    let first = repo.rev_parse(MAIN).unwrap();
    repo.commit_paths(
        MAIN,
        &[change("a.txt", "a\n"), (rp("README.md"), None)],
        "two",
        &opts(),
    )
    .unwrap();
    let second = repo.rev_parse("main").unwrap();
    assert_ne!(first, second);

    let d = repo
        .diff_names(&TreeRef::Oid(first), &TreeRef::Ref("main".into()))
        .unwrap();
    let got: Vec<_> = d.iter().map(|c| (c.path.as_str(), c.kind)).collect();
    assert_eq!(
        got,
        [
            ("README.md", ChangeKind::Deleted),
            ("a.txt", ChangeKind::Added)
        ]
    );

    assert_eq!(
        repo.merge_base("main", &first.to_string()).unwrap(),
        Some(first)
    );
    assert_eq!(repo.read_blob_at("main", "a.txt").unwrap().unwrap(), b"a\n");
    assert_eq!(
        repo.read_blob_at(&first.to_string(), "README.md")
            .unwrap()
            .unwrap(),
        b"hello\n"
    );
    assert!(repo.read_blob_at("main", "nope").unwrap().is_none());
    assert!(repo.rev_parse("no-such-ref").is_err());

    // status: untracked file shows, ignored file does not.
    std::fs::write(dir.path().join(".gitignore"), "*.log\n").unwrap();
    std::fs::write(dir.path().join("new.txt"), "n").unwrap();
    std::fs::write(dir.path().join("x.log"), "n").unwrap();
    let st = repo.status(&StatusOptions::default()).unwrap();
    let paths: Vec<_> = st.iter().map(|e| (e.path.as_str(), e.kind)).collect();
    assert!(
        paths.contains(&("new.txt", StatusKind::Untracked)),
        "{paths:?}"
    );
    assert!(!paths.iter().any(|(p, _)| *p == "x.log"));

    // Ref vs worktree: edit a tracked file and add an untracked one.
    std::fs::write(dir.path().join("a.txt"), "changed\n").unwrap();
    let wt = repo.diff_names(&TreeRef::Head, &TreeRef::WorkTree).unwrap();
    assert!(
        wt.iter()
            .any(|c| c.path == "a.txt" && c.kind == ChangeKind::Modified)
    );
    assert!(
        wt.iter()
            .any(|c| c.path == "new.txt" && c.kind == ChangeKind::Added)
    );
    assert!(wt.iter().all(|c| c.path != "x.log"));
    assert!(repo.diff_names(&TreeRef::WorkTree, &TreeRef::Head).is_err());

    assert_eq!(repo.config_user().is_some(), repo.config_user().is_some());
    assert!(!repo.is_linked_worktree());
    assert_eq!(repo.list_worktrees().unwrap().len(), 1);
}

#[test]
fn rel_path_validation_and_error_codes() {
    for bad in ["", "/abs", "a/../b", "a//b", ".git/config", "a\\b"] {
        let e = RelPath::new(bad).unwrap_err();
        assert_eq!(e.code(), "E-GIT-PATH");
    }
    assert!(RelPath::new("tickets/T-0001/ticket.md").is_ok());
    let dir = tempfile::tempdir().unwrap();
    assert_eq!(
        Repo::discover(dir.path()).unwrap_err().code(),
        "E-GIT-DISCOVER"
    );
}

fn have_git() -> bool {
    std::process::Command::new("git")
        .arg("--version")
        .output()
        .is_ok()
}

#[test]
fn spawn_fallbacks_worktree_merge_push() {
    if !have_git() {
        eprintln!("skipped: git binary absent");
        return;
    }
    let (dir, repo) = fixture();
    let before = repo.runner().spawn_count();
    let wt_dir = tempfile::tempdir().unwrap();
    let wt = wt_dir.path().join("wt");
    repo.worktree_add(&wt, "feature", "main").unwrap();
    let linked = Repo::discover(&wt).unwrap();
    assert!(linked.is_linked_worktree());
    assert_eq!(linked.current_branch().unwrap().as_deref(), Some("feature"));
    assert_eq!(repo.list_worktrees().unwrap().len(), 2);

    // Up to date: no spawn.
    let n = repo.runner().spawn_count();
    assert_eq!(
        repo.merge_branch(&wt, "main").unwrap(),
        gob_git::MergeOutcome::UpToDate
    );
    assert_eq!(repo.runner().spawn_count().since(n), 0);

    // Fast-forward feature to a newer main.
    repo.commit_paths(MAIN, &[change("tickets/m.md", "m\n")], "m", &opts())
        .unwrap();
    assert_eq!(
        repo.merge_branch(&wt, "main").unwrap(),
        gob_git::MergeOutcome::FastForward
    );

    // Conflicts: both sides edit README.md.
    let id = &["-c", "user.name=T", "-c", "user.email=t@e.x"];
    std::fs::write(wt.join("README.md"), "feature\n").unwrap();
    let g = |cwd: &Path, args: &[&str]| {
        let s = std::process::Command::new("git")
            .current_dir(cwd)
            .args(id)
            .args(args)
            .status()
            .unwrap();
        assert!(s.success());
    };
    g(&wt, &["commit", "-am", "f"]);
    repo.commit_paths(MAIN, &[change("README.md", "main\n")], "r", &opts())
        .unwrap();
    assert_eq!(
        linked.merge_branch(&wt, "main").unwrap(),
        gob_git::MergeOutcome::Conflicts(vec!["README.md".into()])
    );
    g(&wt, &["merge", "--abort"]);

    // Push to a bare remote.
    let remote = tempfile::tempdir().unwrap();
    g(remote.path(), &["init", "--bare", "-b", "main"]);
    g(
        dir.path(),
        &["remote", "add", "origin", &remote.path().to_string_lossy()],
    );
    repo.push("origin", "main").unwrap();
    assert!(repo.runner().spawn_count().since(before) >= 3);
}

/// Repo with `core.autocrlf=true` in its local config (T-0030).
fn autocrlf_fixture() -> (tempfile::TempDir, Repo) {
    let dir = tempfile::tempdir().unwrap();
    let repo = Repo::init(dir.path()).unwrap();
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").unwrap();
    let cfg = repo.git_dir().join("config");
    let mut text = std::fs::read_to_string(&cfg).unwrap();
    text.push_str("[core]\n\tautocrlf = true\n");
    std::fs::write(&cfg, text).unwrap();
    let repo = Repo::discover(dir.path()).unwrap();
    repo.commit_paths(MAIN, &[change("README.md", "hello\n")], "root", &opts())
        .unwrap();
    (dir, repo)
}

#[test]
fn crlf_checkout_rewrite_is_not_a_local_edit() {
    let (dir, repo) = autocrlf_fixture();
    repo.commit_paths(MAIN, &[change("tickets/c.md", "a\nb\n")], "add c", &opts())
        .unwrap();
    // What `git checkout` does under autocrlf=true: rewrite the file with CRLF.
    std::fs::write(dir.path().join("tickets/c.md"), "a\r\nb\r\n").unwrap();
    repo.commit_paths(
        MAIN,
        &[change("tickets/c.md", "a\nb\nc\n")],
        "upd c",
        &opts(),
    )
    .expect("a pure line-ending difference must not refuse");
    assert_eq!(
        repo.read_blob_at(MAIN, "tickets/c.md").unwrap().unwrap(),
        b"a\nb\nc\n"
    );
}

#[test]
fn real_edit_still_refused_under_autocrlf() {
    let (dir, repo) = autocrlf_fixture();
    repo.commit_paths(MAIN, &[change("tickets/c.md", "a\nb\n")], "add c", &opts())
        .unwrap();
    std::fs::write(dir.path().join("tickets/c.md"), "a\r\nmine\r\n").unwrap();
    let err = repo
        .commit_paths(
            MAIN,
            &[change("tickets/c.md", "a\nb\nc\n")],
            "upd c",
            &opts(),
        )
        .unwrap_err();
    assert!(matches!(err, GitError::LocalEdits { .. }), "{err}");
}

/// Primary on main plus a linked worktree on `feature`.
fn primary_and_linked() -> (tempfile::TempDir, Repo, tempfile::TempDir, Repo) {
    let (dir, repo) = fixture();
    repo.commit_paths(MAIN, &[change("tickets/a.md", "one\n")], "a", &opts())
        .unwrap();
    let wt_dir = tempfile::tempdir().unwrap();
    let wt = wt_dir.path().join("wt");
    repo.worktree_add(&wt, "feature", "main").unwrap();
    let linked = Repo::discover(&wt).unwrap();
    (dir, repo, wt_dir, linked)
}

#[test]
fn commit_from_linked_worktree_syncs_primary_checkout() {
    if !have_git() {
        eprintln!("skipped: git binary absent");
        return;
    }
    let (dir, repo, _wt_dir, linked) = primary_and_linked();
    let out = linked
        .commit_paths(
            MAIN,
            &[
                change("tickets/a.md", "two\n"),
                change("tickets/b.md", "new\n"),
            ],
            "update",
            &opts(),
        )
        .unwrap();
    assert!(out.unsynced.is_empty());
    assert_eq!(
        std::fs::read_to_string(dir.path().join("tickets/a.md")).unwrap(),
        "two\n"
    );
    assert_eq!(
        std::fs::read_to_string(dir.path().join("tickets/b.md")).unwrap(),
        "new\n"
    );
    let primary = Repo::discover(dir.path()).unwrap();
    assert!(
        primary
            .status(&StatusOptions::default())
            .unwrap()
            .is_empty()
    );
    let again = repo
        .commit_paths(MAIN, &[change("tickets/a.md", "three\n")], "again", &opts())
        .unwrap();
    assert!(again.unsynced.is_empty());
    assert_eq!(
        std::fs::read_to_string(dir.path().join("tickets/a.md")).unwrap(),
        "three\n"
    );
}

#[test]
fn primary_with_local_edit_is_reported_and_keeps_it() {
    if !have_git() {
        eprintln!("skipped: git binary absent");
        return;
    }
    let (dir, repo, _wt_dir, linked) = primary_and_linked();
    let before = repo.rev_parse(MAIN).unwrap();
    std::fs::write(dir.path().join("tickets/a.md"), "mine\n").unwrap();
    let out = linked
        .commit_paths(MAIN, &[change("tickets/a.md", "two\n")], "update", &opts())
        .unwrap();
    assert_ne!(out.oid, before);
    assert_eq!(repo.rev_parse(MAIN).unwrap(), out.oid);
    assert_eq!(out.unsynced.len(), 1);
    assert_eq!(out.unsynced[0].paths_with_local_edits, ["tickets/a.md"]);
    assert_eq!(
        std::fs::read_to_string(dir.path().join("tickets/a.md")).unwrap(),
        "mine\n"
    );
}

// frob:ticket 01M42MGNZZ1BY6YCG49BDHEZAT
// frob:tests primary_with_local_edit_still_receives_the_unblocked_new_paths
#[test]
fn primary_with_local_edit_still_receives_the_unblocked_new_paths() {
    if !have_git() {
        eprintln!("skipped: git binary absent");
        return;
    }
    let (dir, _repo, _wt_dir, linked) = primary_and_linked();
    std::fs::write(dir.path().join("tickets/a.md"), "mine\n").unwrap();
    let out = linked
        .commit_paths(
            MAIN,
            &[
                change("tickets/a.md", "two\n"),
                change("tickets/b.md", "new\n"),
            ],
            "update",
            &opts(),
        )
        .unwrap();
    assert_eq!(out.unsynced.len(), 1);
    assert_eq!(out.unsynced[0].paths_with_local_edits, ["tickets/a.md"]);
    assert_eq!(
        std::fs::read_to_string(dir.path().join("tickets/b.md")).unwrap(),
        "new\n"
    );
    let status = Repo::discover(dir.path())
        .unwrap()
        .status(&StatusOptions::default())
        .unwrap();
    assert!(
        !status.iter().any(|e| format!("{e:?}").contains("b.md")),
        "new path must not appear as a staged deletion: {status:?}"
    );
}

// frob:tests crates/gob-git/src/ledger.rs::Repo.commit_paths_traced
#[test]
fn losing_sync_order_leaves_checkout_equal_to_head() {
    use std::sync::mpsc::channel;
    let (dir, repo) = fixture();
    let (ready_tx, ready_rx) = channel();
    let (go_tx, go_rx) = channel();
    let (done_tx, done_rx) = channel();
    let path = dir.path().to_path_buf();
    // Writer B passes its local-edit check, then waits; A wins the CAS, so B loses and retries.
    let b = std::thread::spawn(move || {
        let repo = Repo::discover(&path).unwrap();
        let mut waited = false;
        repo.commit_paths_with(
            MAIN,
            &[change("tickets/t.md", "new\n")],
            "b",
            &opts(),
            &mut |_| {
                if !std::mem::replace(&mut waited, true) {
                    ready_tx.send(()).unwrap();
                    go_rx.recv().unwrap();
                }
            },
        )
        .unwrap();
        done_tx.send(()).unwrap();
    });
    ready_rx.recv().unwrap();
    // A's ref update lands first, but B fully syncs "new" before A syncs "old".
    repo.commit_paths_traced(
        MAIN,
        &[change("tickets/t.md", "old\n")],
        "a",
        &opts(),
        &mut |_| {},
        &mut || {
            go_tx.send(()).unwrap();
            done_rx.recv().unwrap();
        },
    )
    .unwrap();
    b.join().unwrap();
    let head = repo.read_blob_at(MAIN, "tickets/t.md").unwrap().unwrap();
    assert_eq!(head, b"new\n");
    assert_eq!(
        std::fs::read(dir.path().join("tickets/t.md")).unwrap(),
        b"new\n"
    );
    assert!(repo.status(&StatusOptions::default()).unwrap().is_empty());
}

// frob:ticket 01M4BMRWMJXKXGJ72MTVXFAY3P
// frob:tests crates/gob-git/src/read.rs::Repo.blobs_at
// frob:tests crates/gob-git/src/read.rs::Repo.read_blob
#[test]
fn blobs_listed_in_one_walk_are_read_by_oid() {
    let (_dir, repo) = fixture();
    repo.commit_paths(
        MAIN,
        &[
            change("tickets/a/ticket.md", "A\n"),
            change("tickets/a/events/e1.toml", "E1\n"),
            change("tickets/b/ticket.md", "B\n"),
        ],
        "tree",
        &opts(),
    )
    .unwrap();
    let tip = repo.rev_parse(MAIN).unwrap();
    let all = repo.blobs_at(&format!("{tip}:tickets")).unwrap();
    let paths: Vec<&str> = all.iter().map(|(p, _)| p.as_str()).collect();
    assert_eq!(paths, ["a/events/e1.toml", "a/ticket.md", "b/ticket.md"]);
    for (path, oid) in &all {
        let by_path = repo
            .read_blob_at(MAIN, &format!("tickets/{path}"))
            .unwrap()
            .unwrap();
        assert_eq!(repo.read_blob(oid).unwrap(), by_path, "{path}");
    }
    assert!(repo.blobs_at(&format!("{tip}:nope")).is_err());
}

// frob:ticket 01M4GSVNS3GSRN84QFJSM9W17Q
// frob:tests crates/gob-git/src/ledger.rs::sync_checkout
#[test]
fn a_held_index_lock_is_waited_out_and_the_write_succeeds() {
    let (dir, repo) = fixture();
    let lock = repo.git_dir().join("index.lock");
    std::fs::write(&lock, b"").unwrap();
    let releaser = {
        let lock = lock.clone();
        std::thread::spawn(move || {
            std::thread::sleep(std::time::Duration::from_millis(700));
            std::fs::remove_file(lock).unwrap();
        })
    };
    let out = repo
        .commit_paths(MAIN, &[change("a.txt", "one\n")], "add a", &opts())
        .expect("the writer waits for index.lock instead of failing");
    releaser.join().unwrap();
    assert!(out.unsynced.is_empty());
    assert_eq!(
        std::fs::read_to_string(dir.path().join("a.txt")).unwrap(),
        "one\n"
    );
    assert!(!lock.exists(), "the lock is released");
}
