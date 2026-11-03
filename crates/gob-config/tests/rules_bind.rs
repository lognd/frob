//! Rule binding of the gob-config crate against any host (`ConfigHost` is blanket-implemented).
// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

// frob:tests crates/gob-config/src/rules/mod.rs::bind
#[test]
fn bind_yields_one_rule_per_declared_rule() {
    let rules = gob_config::rules::bind::<()>();
    assert_eq!(rules.len(), gob_config::rules::METAS.len());
}
