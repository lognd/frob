//! Rule binding of the frob-lease crate against any host (`ScopeHost` is blanket-implemented).
// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

// frob:tests crates/frob-lease/src/rules/mod.rs::bind
#[test]
fn bind_yields_one_rule_per_declared_rule() {
    let rules = frob_lease::rules::bind::<()>();
    assert_eq!(rules.len(), frob_lease::rules::METAS.len());
}
