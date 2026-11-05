//! Opaque-region cases of the frob corpus: lexical island fires name a region beside an Unresolved structural rule.

// frob:ticket 01M6ME35JTR9149M74ZPPGV4YY

// The rule crates are linked only for their inventory registrations.
use frob_check as _;

// frob:tests crates/gob-mdtest/src/opaque.rs::assert_product_opaque
#[test]
fn every_frob_opaque_region_is_sound() {
    gob_mdtest::opaque::assert_product_opaque(env!("CARGO_MANIFEST_DIR"), "frob");
}
