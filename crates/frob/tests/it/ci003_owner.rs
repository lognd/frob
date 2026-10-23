//! `CI003` has exactly one declaration in the workspace, and it is the one `grimble-ci` owns.

// frob:ticket 01M5F0A96X8KCH10HNHTXCDEKR

// Linked only for its inventory registrations.
use grimble_ci as _;

use gob_rules::Registry;

/// Looking `CI003` up among the inventory rules and the `grimble-ci` catalogue finds one declaration.
// frob:tests crates/gob-rules/src/registry.rs::Registry.by_id
#[test]
fn ci003_has_exactly_one_declaration_owned_by_grimble_ci() {
    let inventory = Registry::global().by_id("CI003").is_some();
    let owned = grimble_ci::rules::METAS
        .iter()
        .filter(|m| m.id == "CI003")
        .count();
    assert!(!inventory, "frob still declares CI003 in the inventory");
    assert_eq!(owned, 1, "grimble-ci must declare CI003 once");
}
