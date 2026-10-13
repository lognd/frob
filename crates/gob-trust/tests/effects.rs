// frob:ticket 01M3ZX7VYSYT45N8ZKZJQ2DY5D
//! Effect class and grant tests (security.md 2.6).
use gob_trust::effects::{EffectError, Grant, permitted};

#[test]
fn glob_read_does_not_cover_dotenv() {
    let g = Grant::parse("fs.read", "**", None).unwrap();
    assert!(permitted(
        std::slice::from_ref(&g),
        "fs.read",
        "src/a.rs",
        0
    ));
    assert!(!permitted(&[g], "fs.read", ".env", 0));
    let s = Grant::parse("fs.read.secret-shaped", ".env*", None).unwrap();
    assert!(permitted(&[s], "fs.read", ".env", 0));
}

#[test]
fn git_control_grant_is_refused() {
    assert_eq!(
        Grant::parse("fs.write.control", ".git/**", None),
        Err(EffectError::NotGrantable(".git/**".into()))
    );
}

#[test]
fn control_write_needs_control_effect_and_expiry_holds() {
    let w = Grant::parse("fs.write", "**", None).unwrap();
    assert!(!permitted(&[w], "fs.write", "frob.toml", 0));
    let c = Grant::parse("fs.write.control", "frob.toml", Some(10)).unwrap();
    assert!(permitted(
        std::slice::from_ref(&c),
        "fs.write",
        "frob.toml",
        5
    ));
    assert!(!permitted(&[c], "fs.write", "frob.toml", 10));
}
