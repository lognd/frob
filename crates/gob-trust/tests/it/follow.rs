// frob:ticket 01M3ZX7V9AKM8KVBHF32BWEC3K
//! Follow-trust tests (security.md 2.3).
use gob_trust::baseref::BaseRefVerdict;
use gob_trust::follow::{FollowError, FollowRecord, FollowTrust};

const LOCK_NEW: &str = "[[pack]]\nname = \"a\"\nversion = \"2\"\ntree = \"blake3:new\"\n";

fn record() -> FollowRecord {
    FollowRecord::new(
        "refs/remotes/origin/main",
        "https://example.org/r.git",
        "aaa",
    )
    .unwrap()
}

// frob:tests crates/gob-trust/src/follow.rs::FollowRecord.advance
// frob:tests crates/gob-trust/src/follow.rs::FollowRecord.refname
// frob:tests crates/gob-trust/src/follow.rs::FollowRecord.url
// frob:tests crates/gob-trust/src/follow.rs::FollowRecord.tip
// frob:tests crates/gob-trust/src/follow.rs::FollowTrust.decide
// frob:tests crates/gob-trust/src/follow.rs::FollowTrust.from_lock_toml
#[test]
fn pack_changed_on_fetched_ref_is_trusted_without_prompt() {
    let advanced = record().advance("bbb", true).unwrap();
    assert_eq!(advanced.tip(), "bbb");
    assert_eq!(advanced.refname(), "refs/remotes/origin/main");
    assert_eq!(advanced.url(), "https://example.org/r.git");
    let t = FollowTrust::from_lock_toml(LOCK_NEW).unwrap();
    assert!(t.decide("a", "blake3:new").is_trusted());
}

// frob:tests crates/gob-trust/src/follow.rs::FollowTrust.decide
// frob:tests crates/gob-trust/src/follow.rs::FollowTrust.empty
#[test]
fn pair_only_in_unpushed_commit_is_untrusted() {
    // The lock at merge-base(HEAD, tip) lacks the unpushed pair.
    let t = FollowTrust::from_lock_toml("").unwrap();
    assert_eq!(
        t.decide("a", "blake3:new"),
        BaseRefVerdict::UntrustedInChange
    );
    assert_eq!(
        FollowTrust::empty().decide("a", "blake3:new"),
        BaseRefVerdict::UntrustedInChange
    );
}

// frob:tests crates/gob-trust/src/follow.rs::FollowRecord.advance
#[test]
fn tip_moved_by_anything_else_is_ignored() {
    assert!(matches!(
        record().advance("ccc", false),
        Err(FollowError::Moved { .. })
    ));
}

// frob:tests crates/gob-trust/src/follow.rs::FollowRecord.new
#[test]
fn short_refname_is_refused() {
    assert!(FollowRecord::new("origin/main", "u", "t").is_err());
}
