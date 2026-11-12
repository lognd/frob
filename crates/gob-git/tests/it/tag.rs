//! Annotated tag creation, lookup and first-parent history on temporary repositories.

use gob_git::{CommitOptions, GitError, RelPath, Repo};

const MAIN: &str = "refs/heads/main";

fn opts() -> CommitOptions {
    CommitOptions {
        cas_retries: 5,
        author: Some(("Test".into(), "test@example.com".into())),
    }
}

fn commit(repo: &Repo, body: &str, msg: &str) -> gob_git::Oid {
    let change = (
        RelPath::new("f.txt").unwrap(),
        Some(body.as_bytes().to_vec()),
    );
    repo.commit_paths(MAIN, &[change], msg, &opts())
        .unwrap()
        .oid
}

fn fixture() -> (tempfile::TempDir, Repo) {
    let dir = tempfile::tempdir().unwrap();
    let repo = Repo::init(dir.path()).unwrap();
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").unwrap();
    (dir, repo)
}

#[test]
fn an_annotated_tag_peels_to_its_commit_and_is_never_overwritten() {
    // frob:tests crates/gob-git/src/tag.rs::Repo.create_annotated_tag
    // frob:tests crates/gob-git/src/tag.rs::Repo.find_tag
    let (_d, repo) = fixture();
    let c1 = commit(&repo, "1", "first");
    let author = Some(("T".to_owned(), "t@example.com".to_owned()));
    let obj = repo
        .create_annotated_tag("v1", c1, "release v1", author.clone())
        .unwrap();
    let info = repo.find_tag("v1").unwrap().expect("tag exists");
    assert!(info.annotated);
    assert_eq!(info.object, obj);
    assert_eq!(info.commit, c1);
    assert_ne!(obj, c1);
    assert!(repo.find_tag("nope").unwrap().is_none());
    let c2 = commit(&repo, "2", "second");
    let err = repo
        .create_annotated_tag("v1", c2, "again", author)
        .unwrap_err();
    assert!(matches!(err, GitError::Ref(_)), "{err}");
    assert_eq!(repo.find_tag("v1").unwrap().unwrap().commit, c1);
}

#[test]
fn first_parent_subjects_lists_newest_first_and_honours_the_limit() {
    // frob:tests crates/gob-git/src/tag.rs::Repo.first_parent_subjects
    let (_d, repo) = fixture();
    let a = commit(&repo, "1", "first");
    let b = commit(&repo, "2", "second\n\nbody");
    let all = repo.first_parent_subjects("main", 10).unwrap();
    assert_eq!(all, vec![(b, "second".to_owned()), (a, "first".to_owned())]);
    assert_eq!(repo.first_parent_subjects("main", 1).unwrap().len(), 1);
}

// frob:ticket 01M4069XB9N36CQGEBNPKJ5AVG
#[test]
fn list_tags_returns_every_tag_name_sorted() {
    // frob:tests crates/gob-git/src/tag.rs::Repo.list_tags
    let (_d, repo) = fixture();
    assert!(repo.list_tags().unwrap().is_empty());
    let c1 = commit(&repo, "1", "first");
    let author = Some(("T".to_owned(), "t@example.com".to_owned()));
    for name in ["zeta-v1", "frob-v0.0.1", "v0.531.0"] {
        repo.create_annotated_tag(name, c1, "m", author.clone())
            .unwrap();
    }
    assert_eq!(
        repo.list_tags().unwrap(),
        vec!["frob-v0.0.1", "v0.531.0", "zeta-v1"]
    );
}
