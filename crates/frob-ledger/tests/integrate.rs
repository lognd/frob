//! `Ledger::integrate`: create, fast-forward, union-merge and conflict outcomes of a fetched ledger ref.
// frob:ticket 01M5CW049SPSRGGP5ENQD7BPB3

use frob_ledger::branch::init_branch;
use frob_ledger::objects::integrate::Integration;
use frob_ledger::{Ledger, LedgerConfig, RefMode};
use gob_git::{CommitOptions, RelPath, Repo};

const OURS: &str = "refs/heads/frob-tickets";
const THEIRS: &str = "refs/remotes/origin/frob-tickets";

fn fresh() -> (Ledger, Repo) {
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
    let cfg = LedgerConfig {
        mode: RefMode::Orphan,
        branch: "frob-tickets".to_owned(),
        ..LedgerConfig::default()
    };
    let ledger = Ledger::open(
        repo.clone(),
        cfg,
        std::sync::Arc::new(gob_time::SystemClock),
    );
    (ledger, repo)
}

fn put(repo: &Repo, ref_name: &str, path: &str, body: &str) {
    repo.commit_paths(
        ref_name,
        &[(
            RelPath::new(path).expect("path"),
            Some(body.as_bytes().to_vec()),
        )],
        "edit",
        &CommitOptions::default(),
    )
    .expect("commit");
}

// frob:tests crates/frob-ledger/src/integrate.rs::Ledger.integrate
#[test]
fn integrate_creates_fast_forwards_merges_and_reports_conflicts() {
    let (ledger, repo) = fresh();
    init_branch(&repo, "frob-tickets", 5).expect("init");
    let root = repo.rev_parse(OURS).expect("root");

    repo.update_ref_cas(THEIRS, None, root, "seed")
        .expect("seed");
    assert!(matches!(
        ledger.integrate(OURS, THEIRS),
        Ok(Integration::Unchanged)
    ));

    put(&repo, THEIRS, "notes/a.md", "a\n");
    assert!(matches!(
        ledger.integrate(OURS, THEIRS),
        Ok(Integration::FastForward(_))
    ));
    assert_eq!(
        repo.rev_parse(OURS).expect("ours"),
        repo.rev_parse(THEIRS).expect("theirs")
    );

    put(&repo, THEIRS, "notes/b.md", "b\n");
    put(&repo, OURS, "notes/c.md", "c\n");
    let Ok(Integration::Merged { commit, .. }) = ledger.integrate(OURS, THEIRS) else {
        panic!("expected a merge");
    };
    assert_eq!(repo.rev_parse(OURS).expect("ours"), commit);
    for p in ["notes/a.md", "notes/b.md", "notes/c.md"] {
        assert!(repo.read_blob_at(OURS, p).expect("read").is_some(), "{p}");
    }

    put(&repo, THEIRS, "notes/a.md", "theirs\n");
    put(&repo, OURS, "notes/a.md", "ours\n");
    let Ok(Integration::Conflicts(c)) = ledger.integrate(OURS, THEIRS) else {
        panic!("expected a conflict");
    };
    assert_eq!(c[0].path, "notes/a.md");
}

// frob:tests crates/frob-ledger/src/integrate.rs::Ledger.integrate
#[test]
fn integrate_creates_the_local_ref_from_the_remote() {
    let (ledger, repo) = fresh();
    init_branch(&repo, "elsewhere", 5).expect("init");
    let root = repo.rev_parse("refs/heads/elsewhere").expect("root");
    repo.update_ref_cas(THEIRS, None, root, "seed")
        .expect("seed");
    let r = ledger.integrate(OURS, THEIRS);
    assert!(matches!(r, Ok(Integration::Created(_))), "{r:?}");
}

const PM_DOC: &str = "_cycles/01M5CW049SPSRGGP5ENQD7BPB3/cycle.md";

fn diverge_pm_doc() -> (Ledger, Repo) {
    let (ledger, repo) = fresh();
    init_branch(&repo, "frob-tickets", 5).expect("init");
    let root = repo.rev_parse(OURS).expect("root");
    repo.update_ref_cas(THEIRS, None, root, "seed")
        .expect("seed");
    put(&repo, OURS, PM_DOC, "base\n");
    put(&repo, THEIRS, "notes/x.md", "x\n");
    ledger.integrate(OURS, THEIRS).expect("merge base");
    repo.update_ref_cas(THEIRS, None, repo.rev_parse(OURS).expect("ours"), "sync")
        .ok();
    put(&repo, OURS, PM_DOC, "ours\n");
    put(&repo, THEIRS, PM_DOC, "theirs\n");
    (ledger, repo)
}

// frob:tests crates/frob-ledger/src/integrate.rs::Ledger.integrate_with
#[test]
fn pm_docs_changed_on_both_sides_are_refolded_not_conflicted() {
    let (ledger, repo) = diverge_pm_doc();
    let refold = |_: &Ledger, path: &str, _: &str, _: &str| -> Result<String, String> {
        assert_eq!(path, PM_DOC);
        Ok("refolded\n".to_owned())
    };
    let r = ledger.integrate_with(OURS, THEIRS, Some(&refold));
    let Ok(Integration::Merged { refolded, .. }) = r else {
        panic!("expected a merge, got {r:?}");
    };
    assert_eq!(refolded, 1);
    let blob = repo.read_blob_at(OURS, PM_DOC).expect("read");
    assert_eq!(blob.as_deref(), Some(b"refolded\n".as_slice()));
}

// frob:tests crates/frob-ledger/src/integrate.rs::Ledger.integrate_with
#[test]
fn pm_doc_refold_failure_is_a_conflict() {
    let (ledger, _repo) = diverge_pm_doc();
    let refold = |_: &Ledger, _: &str, _: &str, _: &str| -> Result<String, String> {
        Err("no create event".to_owned())
    };
    let r = ledger.integrate_with(OURS, THEIRS, Some(&refold));
    let Ok(Integration::Conflicts(c)) = r else {
        panic!("expected a conflict, got {r:?}");
    };
    assert_eq!(c[0].path, PM_DOC);
    assert!(c[0].reason.contains("no create event"));
    assert!(matches!(
        ledger.integrate(OURS, THEIRS),
        Ok(Integration::Conflicts(_))
    ));
}
