//! Grant ratchet: counts, breadth and the delta against a baseline.

// frob:ticket 01M4GYBTXAPBEX9QYWYX5FKR67

use std::collections::BTreeSet;

use grimble_bind::grants::{ChangeKind, GrantFacts, ratchet};

fn grant(node: &str, atom: &str, files: &[&str], reason: bool) -> GrantFacts {
    GrantFacts {
        node: node.into(),
        atom: atom.into(),
        args: vec![],
        at: None,
        files: files
            .iter()
            .map(|f| (*f).to_owned())
            .collect::<BTreeSet<_>>(),
        has_reason: reason,
        file: "a.grmb".into(),
    }
}

// frob:tests crates/grimble-bind/src/grants.rs::ratchet
#[test]
fn no_baseline_reports_counts_without_delta() {
    let cur = [grant("node/a", "fs.read", &["x", "y"], true)];
    let r = ratchet(&cur, None);
    assert!(!r.has_baseline);
    assert!(r.changes.is_empty());
    assert_eq!((r.nodes[0].grants, r.nodes[0].breadth), (1, 2));
    assert_eq!(r.nodes[0].base_grants, None);
}

// frob:tests crates/grimble-bind/src/grants.rs::ratchet
#[test]
fn widening_is_named_and_narrowing_is_not_a_widening() {
    let base = [
        grant("node/a", "fs.read", &["x"], true),
        grant("node/b", "fs.write", &["p", "q"], true),
    ];
    let cur = [
        grant("node/a", "fs.read", &["x", "y"], true),
        grant("node/b", "fs.write", &["p"], true),
        grant("node/c", "net", &["z"], false),
    ];
    let r = ratchet(&cur, Some(&base));
    let kinds: Vec<_> = r
        .changes
        .iter()
        .map(|c| (c.node.as_str(), c.kind))
        .collect();
    assert_eq!(
        kinds,
        [
            ("node/a", ChangeKind::Widened),
            ("node/c", ChangeKind::Added),
            ("node/b", ChangeKind::Narrowed)
        ]
    );
    assert_eq!((r.changes[0].before, r.changes[0].after), (1, 2));
    assert_eq!(r.unreasoned, ["node/c: net"]);
}

// frob:tests crates/grimble-bind/src/grants.rs::ratchet
#[test]
fn removed_grant_and_node_rows_carry_baseline() {
    let base = [grant("node/a", "fs.read", &["x"], true)];
    let r = ratchet(&[], Some(&base));
    assert_eq!(r.changes[0].kind, ChangeKind::Removed);
    assert_eq!(r.nodes[0].base_grants, Some(1));
    assert_eq!(r.nodes[0].grants, 0);
}
