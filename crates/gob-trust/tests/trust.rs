//! Acceptance and property tests for gob-trust.

use gob_trust::{
    Canonical, CanonicalWriter, MachineKey, TrustError, mac, mac_record, resolve_key_path, verify,
    verify_record,
};
use proptest::prelude::*;

const CTX: &str = "gob-cache-row/v1";

// Acceptance 1: a MAC'd value verifies; one changed byte fails.
#[test]
fn mac_verifies_and_one_byte_change_fails() {
    let key = MachineKey::from_bytes([1; 32]);
    let tag = mac(&key, CTX, b"hello world");
    assert!(verify(&key, CTX, b"hello world", &tag).is_ok());
    assert!(matches!(
        verify(&key, CTX, b"hello worle", &tag),
        Err(TrustError::Mismatch)
    ));
    let other = MachineKey::from_bytes([2; 32]);
    assert!(verify(&other, CTX, b"hello world", &tag).is_err());
}

#[test]
fn domain_separation() {
    let key = MachineKey::from_bytes([1; 32]);
    assert_ne!(
        mac(&key, "gob-cache-row/v1", b"x"),
        mac(&key, "gob-trust-entry/v1", b"x")
    );
    // The context/bytes boundary is unambiguous.
    assert_ne!(mac(&key, "ab", b"c"), mac(&key, "a", b"bc"));
}

struct Rec(&'static str, u64);
impl Canonical for Rec {
    fn write_canonical(&self, w: &mut CanonicalWriter) {
        w.str(self.0).u64(self.1);
    }
}

#[test]
fn record_mac_roundtrip_and_field_boundaries() {
    let key = MachineKey::from_bytes([3; 32]);
    let tag = mac_record(&key, "gob-trust-entry/v1", &Rec("a", 1));
    assert!(verify_record(&key, "gob-trust-entry/v1", &Rec("a", 1), &tag).is_ok());
    assert!(verify_record(&key, "gob-trust-entry/v1", &Rec("a", 2), &tag).is_err());
    assert!(verify_record(&key, "gob-trust-entry/v1", &Rec("b", 1), &tag).is_err());
}

#[test]
fn tag_hex_roundtrip_and_debug_redaction() {
    let key = MachineKey::from_bytes([9; 32]);
    let tag = mac(&key, CTX, b"x");
    assert_eq!(gob_trust::Tag::from_hex(&tag.to_hex()), Some(tag));
    assert_eq!(gob_trust::Tag::from_hex("zz"), None);
    let dbg = format!("{key:?}");
    assert_eq!(dbg, "MachineKey(<redacted>)");
}

#[test]
fn env_key_parsing() {
    // Variable names are unique to this test; no other test reads them.
    assert!(matches!(
        MachineKey::from_env_var("GOB_TRUST_TEST_UNSET_VAR"),
        Err(TrustError::BadEnvKey { .. })
    ));
}

#[test]
fn path_resolution() {
    // `/x/cfg` is not absolute on Windows (no drive), so build the base from a real absolute path.
    let base = std::env::temp_dir().join("cfg");
    let want = base.clone();
    let p =
        resolve_key_path(move |k| (k == "XDG_CONFIG_HOME").then(|| base.clone().into_os_string()))
            .unwrap();
    assert_eq!(p, want.join("gob").join("machine.key"));
    // A relative XDG_CONFIG_HOME is ignored (XDG spec), with no HOME that is an error.
    let e = resolve_key_path(|k| (k == "XDG_CONFIG_HOME").then(|| "rel".into()));
    assert!(matches!(e, Err(TrustError::NoConfigDir)));
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        let p = resolve_key_path(|k| (k == "HOME").then(|| "/home/u".into())).unwrap();
        assert_eq!(p, std::path::Path::new("/home/u/.config/gob/machine.key"));
    }
}

// Acceptance 2: first use creates an owner-only key; an open one is a typed error.
#[cfg(unix)]
mod files {
    use super::*;
    use std::os::unix::fs::PermissionsExt;

    fn mode(p: &std::path::Path) -> u32 {
        std::fs::metadata(p).unwrap().permissions().mode() & 0o777
    }

    #[test]
    fn first_use_creates_owner_only_key_and_reload_is_stable() {
        let d = tempfile::tempdir().unwrap();
        let path = d.path().join("cfg/gob/machine.key");
        let a = MachineKey::load_or_create_at(&path).unwrap();
        assert_eq!(mode(&path), 0o600);
        assert_eq!(std::fs::metadata(&path).unwrap().len(), 32);
        let b = MachineKey::load_or_create_at(&path).unwrap();
        assert_eq!(mac(&a, CTX, b"x"), mac(&b, CTX, b"x"));
        // No temp files left behind.
        let n = std::fs::read_dir(path.parent().unwrap()).unwrap().count();
        assert_eq!(n, 1);
    }

    #[test]
    fn open_permissions_are_typed_errors() {
        let d = tempfile::tempdir().unwrap();
        let path = d.path().join("machine.key");
        std::fs::write(&path, [0u8; 32]).unwrap();
        for bad in [0o640, 0o604, 0o620, 0o666, 0o660] {
            std::fs::set_permissions(&path, std::fs::Permissions::from_mode(bad)).unwrap();
            match MachineKey::load_or_create_at(&path) {
                Err(e @ TrustError::InsecurePermissions { .. }) => {
                    let msg = e.to_string();
                    assert!(msg.contains(path.to_str().unwrap()) && msg.contains("chmod 600"));
                }
                other => panic!("mode {bad:o}: {other:?}"),
            }
        }
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o400)).unwrap();
        assert!(MachineKey::load_or_create_at(&path).is_ok());
    }

    #[test]
    fn wrong_length_is_malformed() {
        let d = tempfile::tempdir().unwrap();
        let path = d.path().join("machine.key");
        std::fs::write(&path, [0u8; 5]).unwrap();
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600)).unwrap();
        assert!(matches!(
            MachineKey::load_or_create_at(&path),
            Err(TrustError::Malformed { .. })
        ));
    }
}

#[test]
fn concurrent_first_use_yields_one_key() {
    let d = tempfile::tempdir().unwrap();
    let path = d.path().join("gob/machine.key");
    for _ in 0..20 {
        let _ = std::fs::remove_dir_all(d.path().join("gob"));
        let barrier = std::sync::Arc::new(std::sync::Barrier::new(2));
        let tags: Vec<_> = (0..2)
            .map(|_| {
                let (p, b) = (path.clone(), barrier.clone());
                std::thread::spawn(move || {
                    b.wait();
                    let k = MachineKey::load_or_create_at(&p).unwrap();
                    mac(&k, CTX, b"x")
                })
            })
            .collect::<Vec<_>>()
            .into_iter()
            .map(|h| h.join().unwrap())
            .collect();
        assert_eq!(tags[0], tags[1]);
        assert_eq!(
            std::fs::read_dir(path.parent().unwrap()).unwrap().count(),
            1
        );
    }
}

proptest! {
    #[test]
    fn any_one_byte_change_changes_the_tag(
        data in proptest::collection::vec(any::<u8>(), 1..256),
        idx in any::<prop::sample::Index>(),
        flip in 1u8..=255,
    ) {
        let key = MachineKey::from_bytes([5; 32]);
        let tag = mac(&key, CTX, &data);
        let mut changed = data.clone();
        let i = idx.index(data.len());
        changed[i] ^= flip;
        prop_assert!(verify(&key, CTX, &changed, &tag).is_err());
        prop_assert!(verify(&key, CTX, &data, &tag).is_ok());
    }
}
