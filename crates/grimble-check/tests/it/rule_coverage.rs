//! Every registered grimble rule has an mdtest fire/clean pair or a fixture, or a ticketed allowlist entry.

// frob:ticket 01M47QTTKVRY3C52CXZBGB8V55

// The rule crates are linked only for their inventory registrations.
use grimble_bind as _;
use grimble_check as _;
use grimble_model as _;

// frob:tests crates/gob-mdtest/src/coverage.rs::assert_product_coverage
#[test]
fn every_grimble_rule_has_a_corpus() {
    gob_mdtest::coverage::assert_product_coverage(env!("CARGO_MANIFEST_DIR"), "grimble");
}
