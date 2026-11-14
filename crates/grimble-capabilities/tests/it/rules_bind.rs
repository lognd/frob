//! Rule binding of the capability pack rules against a stub host.
// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use grimble_capabilities::pack_rules::PackHost;

/// A host whose pack pass examined no subjects.
struct Stub;

impl PackHost for Stub {
    fn subjects_of(&self, _id: &str) -> usize {
        0
    }
}

// frob:tests crates/grimble-capabilities/src/rules/mod.rs::bind
#[test]
fn bind_yields_one_rule_per_declared_rule() {
    let rules = grimble_capabilities::rules::bind::<Stub>();
    assert_eq!(rules.len(), grimble_capabilities::rules::METAS.len());
}
