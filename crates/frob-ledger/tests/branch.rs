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
