//! The digest scheme number is defined once, in gob-caps.

// frob:ticket 01M4M52WDAB9VH3PJ2VDF2JFRY

// frob:tests crates/gob-ir/src/digest.rs::DIGEST_SCHEME
#[test]
fn digest_scheme_is_one_constant() {
    assert_eq!(gob_ir::DIGEST_SCHEME, gob_caps::DIGEST_SCHEME);
}
