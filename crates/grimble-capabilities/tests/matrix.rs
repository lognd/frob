//! Matrix cell tests (grimble-model.md 9.6).

use grimble_capabilities::{Cell, NodeInput, build};

fn node(name: &str, lang: &str) -> NodeInput {
    NodeInput {
        node: name.to_owned(),
        lang: lang.to_owned(),
        ..NodeInput::default()
    }
}

// frob:tests crates/grimble-capabilities/src/lib.rs::build
#[test]
fn no_detector_is_unknown_with_one_unresolved_per_node() {
    let nodes = [node("legacy", "cobol")];
    let m = build(&nodes, &["net.connect", "fs.write"]);
    assert_eq!(m.cells["legacy"]["net.connect"], Cell::Unknown);
    assert_eq!(m.cells["legacy"]["fs.write"], Cell::Unknown);
    assert_eq!(m.unresolved.len(), 1);
    assert_eq!(m.unresolved[0].node, "legacy");
    assert_eq!(m.unresolved[0].atoms.len(), 2);
}

// frob:tests crates/grimble-capabilities/src/lib.rs::build
#[test]
fn not_applicable_is_never_unresolved() {
    let m = build(&[node("style", "css")], &["net.connect"]);
    assert_eq!(m.cells["style"]["net.connect"], Cell::NotApplicable);
    assert!(m.unresolved.is_empty());
}

// frob:tests crates/grimble-capabilities/src/lib.rs::build
#[test]
fn rust_cells_follow_grants_and_uses() {
    let mut n = node("core", "rust");
    n.uses.insert("net.connect".into());
    n.grants.insert("fs".into());
    let m = build(&[n], &["net.connect", "fs.write"]);
    assert_eq!(m.cells["core"]["net.connect"], Cell::Undeclared);
    assert_eq!(m.cells["core"]["fs.write"], Cell::DeclaredUnused);
    assert!(m.unresolved.is_empty());
}

// frob:tests crates/grimble-capabilities/src/lib.rs::Cell.as_str
#[test]
fn cell_spellings_are_the_model_spellings() {
    assert_eq!(Cell::DeclaredUnused.as_str(), "declared-unused");
    assert_eq!(Cell::NotApplicable.as_str(), "not-applicable");
    assert_eq!(Cell::Unknown.as_str(), "unknown");
}
