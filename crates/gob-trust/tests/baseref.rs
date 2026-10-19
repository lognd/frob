// frob:ticket 01M3ZX7V587K71E94E0AE4GWW8
//! Base-ref trust tests (security.md 2.3).
use gob_trust::baseref::{BaseRefTrust, BaseRefVerdict};

const LOCK: &str = "[[pack]]\nname = \"a\"\nversion = \"1\"\ntree = \"blake3:aaa\"\n[pack.effects]\nfs = [\"read:src/**\"]\n";

// frob:tests crates/gob-trust/src/baseref.rs::BaseRefTrust.decide
#[test]
fn digest_differing_from_lock_is_untrusted_in_change() {
    let t = BaseRefTrust::from_lock_toml(LOCK).unwrap();
    assert_eq!(
        t.decide("a", "blake3:zzz"),
        BaseRefVerdict::UntrustedInChange
    );
    assert_eq!(
        t.decide("new", "blake3:aaa"),
        BaseRefVerdict::UntrustedInChange
    );
}

// frob:tests crates/gob-trust/src/baseref.rs::BaseRefTrust.decide
#[test]
fn unchanged_pack_gets_recorded_effects() {
    let t = BaseRefTrust::from_lock_toml(LOCK).unwrap();
    let v = t.decide("a", "blake3:aaa");
    assert!(v.is_trusted());
    assert_eq!(
        BaseRefTrust::empty().decide("a", "blake3:aaa"),
        BaseRefVerdict::UntrustedInChange
    );
}

// frob:tests crates/gob-trust/src/baseref.rs::BaseRefTrust.from_lock_toml
#[test]
fn malformed_lock_is_refused() {
    assert!(BaseRefTrust::from_lock_toml("pack = 3").is_err());
}
