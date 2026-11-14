//! Rule binding of the bind crate against a stub host.
// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use grimble_bind::host::BindHost;

/// A host that examined no subjects.
struct Stub;

impl BindHost for Stub {
    fn subjects_of(&self, _id: &str) -> usize {
        0
    }
}

// frob:tests crates/grimble-bind/src/rules/mod.rs::bind
#[test]
fn bind_yields_one_rule_per_declared_rule() {
    let rules = grimble_bind::rules::bind::<Stub>();
    assert_eq!(rules.len(), grimble_bind::rules::METAS.len());
}
