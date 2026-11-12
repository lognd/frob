//! `init_branch`: orphan ticket branch bootstrap through compare-and-swap.
// frob:ticket 01M3ZX8141MTBF6G2E6BAD33TS

use frob_ledger::branch::{BranchInit, init_branch};
use gob_git::{CommitOptions, RelPath, Repo};

fn fresh() -> Repo {
    let dir = tempfile::tempdir().expect("tempdir").keep();
    let repo = Repo::init(&dir).expect("init");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
    let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
    std::fs::write(
        repo.git_dir().join("config"),
        format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
    )
    .expect("identity");
    drop(repo);
    let repo = Repo::discover(&dir).expect("discover");
    repo.commit_paths(
        "refs/heads/main",
        &[(
            RelPath::new("code.txt").expect("path"),
            Some(b"hi\n".to_vec()),
        )],
        "root",
        &CommitOptions::default(),
    )
    .expect("root commit");
    repo
}

// frob:tests crates/frob-ledger/src/branch.rs::init_branch
#[test]
fn creates_then_reports_already_and_leaves_main_alone() {
    let repo = fresh();
    let main = repo.rev_parse("refs/heads/main").expect("main");
    let first = init_branch(&repo, "frob-tickets", 5).expect("create");
    let BranchInit::Created(tip) = first else {
        panic!("expected Created, got {first:?}");
    };
    assert_eq!(repo.rev_parse("refs/heads/frob-tickets").expect("tip"), tip);
    assert_eq!(repo.rev_parse("refs/heads/main").expect("main"), main);
    assert_eq!(
        init_branch(&repo, "frob-tickets", 5).expect("again"),
        BranchInit::Already(tip)
    );
}

// frob:tests crates/frob-ledger/src/branch.rs::init_branch
#[test]
fn bad_names_are_refused_before_any_write() {
    let repo = fresh();
    assert!(init_branch(&repo, "a..b", 5).is_err());
    assert!(repo.rev_parse("refs/heads/a..b").is_err());
}

/// Run `git` in `dir`, panicking on failure.
fn git(dir: &std::path::Path, args: &[&str]) {
    let out = std::process::Command::new("git")
        .current_dir(dir)
        .args(args)
        .output()
        .expect("spawn git");
    assert!(
        out.status.success(),
        "git {args:?}: {}",
        String::from_utf8_lossy(&out.stderr)
    );
}

/// A bare `origin` holding `main` and a ledger branch `frob-tickets` with one extra commit.
fn origin_with_ticket_branch() -> (std::path::PathBuf, gob_git::Oid) {
    let work = fresh();
    let dir = work.work_dir().expect("work dir").to_path_buf();
    init_branch(&work, "frob-tickets", 5).expect("create");
    work.commit_paths(
        "refs/heads/frob-tickets",
        &[(
            RelPath::new("note.txt").expect("path"),
            Some(b"x\n".to_vec()),
        )],
        "tickets: second",
        &CommitOptions::default(),
    )
    .expect("second commit");
    let tip = work.rev_parse("refs/heads/frob-tickets").expect("tip");
    let bare = tempfile::tempdir().expect("tempdir").keep();
    git(
        &bare,
        &[
            "clone",
            "--bare",
            gob_path::Shown::with_home(&dir, None).as_str(),
            "o.git",
        ],
    );
    (bare.join("o.git"), tip)
}

// frob:tests crates/frob-ledger/src/branch.rs::init_branch
#[test]
fn adopts_origin_tracking_ref_instead_of_forking() {
    let (origin, tip) = origin_with_ticket_branch();
    let clones = tempfile::tempdir().expect("tempdir").keep();
    git(
        &clones,
        &[
            "clone",
            gob_path::Shown::with_home(&origin, None).as_str(),
            "c",
        ],
    );
    let dir = clones.join("c");
    git(&dir, &["config", "user.name", "Test User"]);
    git(&dir, &["config", "user.email", "test@example.com"]);
    git(&dir, &["branch", "-D", "-r", "origin/HEAD"]);
    let repo = Repo::discover(&dir).expect("discover");
    assert!(repo.rev_parse("refs/heads/frob-tickets").is_err());
    assert_eq!(
        init_branch(&repo, "frob-tickets", 5).expect("adopt"),
        BranchInit::Adopted(tip)
    );
    assert_eq!(
        repo.rev_parse("refs/heads/frob-tickets").expect("local"),
        tip
    );
}

// frob:tests crates/frob-ledger/src/branch.rs::init_branch
#[test]
fn shallow_single_branch_clone_fetches_the_ticket_branch() {
    let (origin, tip) = origin_with_ticket_branch();
    let clones = tempfile::tempdir().expect("tempdir").keep();
    let url = format!(
        "file://{}",
        gob_path::Shown::with_home(&origin, None).as_str()
    );
    git(
        &clones,
        &["clone", "--depth=1", "--branch", "main", &url, "c"],
    );
    let dir = clones.join("c");
    git(&dir, &["config", "user.name", "Test User"]);
    git(&dir, &["config", "user.email", "test@example.com"]);
    let repo = Repo::discover(&dir).expect("discover");
    assert!(repo.is_shallow());
    assert!(repo.rev_parse("refs/remotes/origin/frob-tickets").is_err());
    assert_eq!(
        init_branch(&repo, "frob-tickets", 5).expect("adopt"),
        BranchInit::Adopted(tip)
    );
    assert_eq!(
        repo.rev_parse("refs/heads/frob-tickets").expect("local"),
        tip
    );
}

// frob:tests crates/frob-ledger/src/branch.rs::init_branch
#[test]
fn origin_without_the_branch_still_gets_a_fresh_orphan() {
    let (origin, _) = origin_with_ticket_branch();
    let clones = tempfile::tempdir().expect("tempdir").keep();
    let url = format!(
        "file://{}",
        gob_path::Shown::with_home(&origin, None).as_str()
    );
    git(&clones, &["clone", &url, "c"]);
    let dir = clones.join("c");
    git(&dir, &["config", "user.name", "Test User"]);
    git(&dir, &["config", "user.email", "test@example.com"]);
    let repo = Repo::discover(&dir).expect("discover");
    assert!(matches!(
        init_branch(&repo, "other-tickets", 5).expect("orphan"),
        BranchInit::Created(_)
    ));
}

/// Commit `.gitattributes` text onto the ticket branch, standing in for a branch made before the pin.
fn set_attrs(repo: &Repo, text: &str) {
    repo.commit_paths(
        "refs/heads/frob-tickets",
        &[(
            RelPath::new(".gitattributes").expect("path"),
            Some(text.as_bytes().to_vec()),
        )],
        "tickets: legacy attrs",
        &CommitOptions::default(),
    )
    .expect("legacy attrs");
}

/// The `.gitattributes` text on the ticket branch.
fn attrs(repo: &Repo) -> String {
    let blob = repo
        .read_blob_at("refs/heads/frob-tickets", ".gitattributes")
        .expect("read")
        .expect("present");
    String::from_utf8(blob).expect("utf8")
}

// frob:ticket 01M5J931Y2JCF9J0XFVRP71BER
// frob:tests crates/frob-ledger/src/branch.rs::init_branch
#[test]
fn backfills_the_pin_once_and_keeps_user_lines() {
    let repo = fresh();
    init_branch(&repo, "frob-tickets", 5).expect("create");
    set_attrs(&repo, "*/*.md merge=frob\ncustom.bin -text");
    let BranchInit::Already(tip) = init_branch(&repo, "frob-tickets", 5).expect("backfill") else {
        panic!("expected Already");
    };
    assert_eq!(repo.rev_parse("refs/heads/frob-tickets").expect("tip"), tip);
    let text = attrs(&repo);
    assert_eq!(
        text,
        "*/*.md merge=frob\ncustom.bin -text\n*.md text eol=lf\n*.toml text eol=lf\n"
    );
    assert_eq!(
        init_branch(&repo, "frob-tickets", 5).expect("again"),
        BranchInit::Already(tip),
        "second run must not commit"
    );
    assert_eq!(attrs(&repo), text);
}

// frob:ticket 01M5J931Y2JCF9J0XFVRP71BER
// frob:tests crates/frob-ledger/src/branch.rs::init_branch
#[test]
fn partial_pin_adds_only_the_missing_glob_and_respects_user_eol() {
    let repo = fresh();
    init_branch(&repo, "frob-tickets", 5).expect("create");
    set_attrs(&repo, "*.md text eol=crlf\n");
    init_branch(&repo, "frob-tickets", 5).expect("backfill");
    assert_eq!(attrs(&repo), "*.md text eol=crlf\n*.toml text eol=lf\n");
}

// frob:ticket 01M5J931Y2JCF9J0XFVRP71BER
// frob:tests crates/frob-ledger/src/branch.rs::init_branch
#[test]
fn missing_attributes_file_gets_the_pin() {
    let repo = fresh();
    init_branch(&repo, "frob-tickets", 5).expect("create");
    repo.commit_paths(
        "refs/heads/frob-tickets",
        &[(RelPath::new(".gitattributes").expect("path"), None)],
        "tickets: drop attrs",
        &CommitOptions::default(),
    )
    .expect("delete");
    init_branch(&repo, "frob-tickets", 5).expect("backfill");
    assert_eq!(attrs(&repo), "*.md text eol=lf\n*.toml text eol=lf\n");
}

// frob:ticket 01M5J931Y2JCF9J0XFVRP71BER
// frob:tests crates/frob-ledger/src/branch.rs::init_branch
#[test]
fn a_locked_branch_is_left_as_is_without_failing() {
    let repo = fresh();
    // A ref that cannot be advanced (locked) keeps its tip and still reports Already.
    init_branch(&repo, "frob-tickets", 5).expect("create");
    set_attrs(&repo, "*.md text\n");
    let lock = repo.git_dir().join("refs/heads/frob-tickets.lock");
    std::fs::write(&lock, "").expect("lock");
    let before = repo.rev_parse("refs/heads/frob-tickets").expect("tip");
    assert_eq!(
        init_branch(&repo, "frob-tickets", 1).expect("tolerated"),
        BranchInit::Already(before)
    );
    assert_eq!(
        repo.rev_parse("refs/heads/frob-tickets").expect("tip"),
        before
    );
}
