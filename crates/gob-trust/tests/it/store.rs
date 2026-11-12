//! Acceptance tests for the trust store (security.md 2.3).

use std::path::PathBuf;

use gob_trust::{
    DEFAULT_TTL_SECS, Expiry, Finding, MachineKey, NETWORK_TTL_SECS, RepoIdentity, TrustStore,
    Verdict,
};

const NOW: u64 = 1_000_000;

fn ident(commit: &str) -> RepoIdentity {
    RepoIdentity {
        root: PathBuf::from("/work/repo"),
        root_commit: commit.to_owned(),
        remote_url: "https://example.com/r.git".to_owned(),
    }
}

fn open(dir: &tempfile::TempDir) -> TrustStore {
    TrustStore::open(
        &dir.path().join("trust.toml"),
        MachineKey::from_bytes([9; 32]),
    )
    .unwrap()
}

// frob:tests crates/gob-trust/src/store/mod.rs::TrustStore
#[test]
fn grant_then_consult_trusts_matching_identity() {
    let d = tempfile::tempdir().unwrap();
    let mut s = open(&d);
    s.grant(ident("abc"), "digest1", "alice", NOW, false)
        .unwrap();
    assert!(matches!(
        s.consult(&ident("abc"), "digest1", NOW + 1),
        Verdict::Trusted(_)
    ));
    // Survives a reload.
    let s = open(&d);
    assert!(matches!(
        s.consult(&ident("abc"), "digest1", NOW + 1),
        Verdict::Trusted(_)
    ));
}

// frob:tests crates/gob-trust/src/store/mod.rs::TrustStore
#[test]
fn differing_root_commit_root_or_remote_does_not_match() {
    let d = tempfile::tempdir().unwrap();
    let mut s = open(&d);
    s.grant(ident("abc"), "digest1", "alice", NOW, false)
        .unwrap();
    assert_eq!(s.consult(&ident("zzz"), "digest1", NOW), Verdict::Untrusted);
    let mut moved = ident("abc");
    moved.root = PathBuf::from("/elsewhere");
    assert_eq!(s.consult(&moved, "digest1", NOW), Verdict::Untrusted);
    let mut remote = ident("abc");
    remote.remote_url = "https://evil.example/r.git".to_owned();
    assert_eq!(s.consult(&remote, "digest1", NOW), Verdict::Untrusted);
    assert_eq!(s.consult(&ident("abc"), "other", NOW), Verdict::Untrusted);
}

// frob:tests crates/gob-trust/src/store/mod.rs::TrustStore
#[test]
fn hand_added_unmaced_entry_is_inert() {
    let d = tempfile::tempdir().unwrap();
    let path = d.path().join("trust.toml");
    std::fs::write(
        &path,
        "[[entry]]\nsubject = \"d\"\nwho = \"me\"\nroot = \"/work/repo\"\nroot_commit = \"abc\"\n\
         remote_url = \"https://example.com/r.git\"\ngranted_at = 1\nexpires_at = 99999999999\n\
         network = false\n",
    )
    .unwrap();
    let s = TrustStore::open(&path, MachineKey::from_bytes([9; 32])).unwrap();
    assert_eq!(s.consult(&ident("abc"), "d", NOW), Verdict::Untrusted);
    assert!(s.doctor(NOW).contains(&Finding::InertLines { count: 1 }));
}

// frob:tests crates/gob-trust/src/store/mod.rs::TrustStore
#[test]
fn tampered_expiry_or_wrong_key_is_inert() {
    let d = tempfile::tempdir().unwrap();
    let mut s = open(&d);
    s.grant(ident("abc"), "d", "alice", NOW, false).unwrap();
    let path = d.path().join("trust.toml");
    let text = std::fs::read_to_string(&path).unwrap();
    let forged = text.replace(
        &format!("expires_at = {}", NOW + DEFAULT_TTL_SECS),
        "expires_at = 99999999999",
    );
    assert_ne!(text, forged);
    std::fs::write(&path, forged).unwrap();
    assert_eq!(
        open(&d).consult(&ident("abc"), "d", NOW),
        Verdict::Untrusted
    );
    std::fs::write(&path, text).unwrap();
    let other = TrustStore::open(&path, MachineKey::from_bytes([1; 32])).unwrap();
    assert_eq!(other.consult(&ident("abc"), "d", NOW), Verdict::Untrusted);
}

// frob:tests crates/gob-trust/src/store/mod.rs::TrustStore
#[test]
fn expired_entry_is_untrusted_and_doctor_reports_it() {
    let d = tempfile::tempdir().unwrap();
    let mut s = open(&d);
    let id = s.grant(ident("abc"), "d", "alice", NOW, false).unwrap();
    let late = NOW + DEFAULT_TTL_SECS;
    assert!(matches!(
        s.consult(&ident("abc"), "d", late),
        Verdict::Expired(_)
    ));
    assert!(s.doctor(late).contains(&Finding::ExpiredEntry {
        id,
        subject: "d".to_owned()
    }));
    assert!(
        !s.doctor(NOW)
            .iter()
            .any(|f| matches!(f, Finding::ExpiredEntry { .. }))
    );
}

// frob:tests crates/gob-trust/src/store/mod.rs::TrustStore
#[test]
fn network_grants_live_180_days() {
    let d = tempfile::tempdir().unwrap();
    let mut s = open(&d);
    s.grant(ident("abc"), "n", "alice", NOW, true).unwrap();
    let (e, ex) = s.list(NOW + DEFAULT_TTL_SECS)[0];
    assert_eq!(ex, Expiry::Live);
    assert_eq!(e.expires_at(), NOW + NETWORK_TTL_SECS);
}

// frob:tests crates/gob-trust/src/store/mod.rs::TrustStore
#[test]
fn revoke_removes_entry_and_persists() {
    let d = tempfile::tempdir().unwrap();
    let mut s = open(&d);
    let id = s.grant(ident("abc"), "d", "alice", NOW, false).unwrap();
    assert!(!s.revoke("nope").unwrap());
    assert!(s.revoke(&id).unwrap());
    assert!(open(&d).list(NOW).is_empty());
}

#[cfg(unix)]
// frob:tests crates/gob-trust/src/store/mod.rs::TrustStore
#[test]
fn doctor_reports_group_writable_store() {
    use std::os::unix::fs::PermissionsExt;
    let d = tempfile::tempdir().unwrap();
    let mut s = open(&d);
    s.grant(ident("abc"), "d", "alice", NOW, false).unwrap();
    let path = d.path().join("trust.toml");
    assert!(
        !s.doctor(NOW)
            .iter()
            .any(|f| matches!(f, Finding::WritableStore { .. }))
    );
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o664)).unwrap();
    assert!(
        s.doctor(NOW)
            .iter()
            .any(|f| matches!(f, Finding::WritableStore { .. }))
    );
}

// frob:tests crates/gob-trust/src/store/entry.rs::Entry.id
// frob:tests crates/gob-trust/src/store/entry.rs::Entry.identity
// frob:tests crates/gob-trust/src/store/entry.rs::Entry.subject
// frob:tests crates/gob-trust/src/store/entry.rs::Entry.expires_at
// frob:tests crates/gob-trust/src/store/entry.rs::Entry.expiry
// frob:tests crates/gob-trust/src/store/entry.rs::Entry.root
#[test]
fn entry_accessors_report_what_was_granted() {
    let d = tempfile::tempdir().unwrap();
    let mut s = open(&d);
    let id = s.grant(ident("abc"), "d", "alice", NOW, false).unwrap();
    let (e, ex) = s.list(NOW)[0];
    assert_eq!(e.id(), id);
    assert_eq!(e.identity(), &ident("abc"));
    assert_eq!(e.subject(), "d");
    assert_eq!(e.root(), std::path::Path::new("/work/repo"));
    assert_eq!(e.expires_at(), NOW + DEFAULT_TTL_SECS);
    assert_eq!(
        (ex, e.expiry(NOW + DEFAULT_TTL_SECS)),
        (Expiry::Live, Expiry::Expired)
    );
}

// frob:tests crates/gob-trust/src/store/mod.rs::default_store_path
#[test]
fn default_store_path_sits_beside_the_machine_key() {
    if let Ok(p) = gob_trust::default_store_path() {
        assert_eq!(p.file_name().unwrap(), "trust.toml");
        assert_eq!(p.parent(), gob_trust::default_key_path().unwrap().parent());
    }
}
