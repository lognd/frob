//! `release adopt` resolution on temporary repositories with hand-made tags; git is only read.
// frob:ticket 01M4235FC39ZQYF207H8ANQEZE

use std::fs;

use frob_release::adopt::{AdoptError, resolve};
use frob_release::rel001::evaluate;

mod rel001_corpus;
use rel001_corpus::{commit, fixture, tag};

#[test]
fn hand_made_annotated_and_lightweight_tags_resolve_to_the_cut_they_would_have_recorded() {
    // frob:tests crates/frob-release/src/adopt.rs::resolve
    let (dir, repo) = fixture();
    let c = commit(&repo, "0.0.1");
    let annotated = tag(&repo, "frob-v0.0.1", c);
    fs::create_dir_all(repo.git_dir().join("refs/tags")).unwrap();
    fs::write(
        repo.git_dir().join("refs/tags/grimble-v0.0.1"),
        format!("{c}\n"),
    )
    .unwrap();
    let before = fs::read_to_string(repo.git_dir().join("refs/tags/grimble-v0.0.1")).unwrap();

    let data = resolve(dir.path(), "0.0.1").unwrap();
    assert_eq!(data.version, "0.0.1");
    assert_eq!(data.commit, c.to_string());
    assert_eq!(data.tags.len(), 2);
    assert_eq!(data.tags[0], annotated);
    assert_eq!(data.tags[1].name, "grimble-v0.0.1");
    assert_eq!(
        data.tags[1].object,
        c.to_string(),
        "a lightweight tag is its commit"
    );
    // Git is untouched and the resolved cut silences REL001.
    assert_eq!(
        fs::read_to_string(repo.git_dir().join("refs/tags/grimble-v0.0.1")).unwrap(),
        before
    );
    assert!(evaluate(&repo, &[data]).findings.is_empty());
}

#[test]
fn a_missing_tag_is_refused_naming_every_missing_tag() {
    // frob:tests crates/frob-release/src/adopt.rs::resolve
    // frob:tests crates/frob-release/src/adopt.rs::AdoptError.is_refusal
    // frob:tests crates/frob-release/src/adopt.rs::AdoptError.remedy
    let (dir, repo) = fixture();
    let c = commit(&repo, "0.0.1");
    tag(&repo, "frob-v0.0.1", c);
    let err = resolve(dir.path(), "0.0.1").unwrap_err();
    assert!(
        matches!(&err, AdoptError::MissingTags(m) if m == &["grimble-v0.0.1"]),
        "{err}"
    );
    assert!(err.is_refusal());
    assert!(err.remedy("0.0.1").contains("frob.toml"));
    let none = resolve(dir.path(), "0.0.2").unwrap_err();
    assert!(
        matches!(&none, AdoptError::MissingTags(m) if m.len() == 2),
        "{none}"
    );
}

#[test]
fn a_bad_version_is_refused() {
    // frob:tests crates/frob-release/src/adopt.rs::resolve
    let (dir, _repo) = fixture();
    let err = resolve(dir.path(), "v0.0.1").unwrap_err();
    assert!(matches!(err, AdoptError::InvalidVersion(_)), "{err}");
}
