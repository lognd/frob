//! Grant ratchet: counts, breadth and the delta against a baseline.

// frob:ticket 01M4GYBTXAPBEX9QYWYX5FKR67
// frob:ticket 01M4GYBZZB9Z4QPMW451DC0JFG

use std::collections::BTreeSet;

use grimble_bind::grants::{ChangeKind, GrantFacts, ratchet, trust_zones};

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

// frob:tests crates/grimble-bind/src/grants.rs::ChangeKind.as_str
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

fn at(node: &str, atom: &str, glob: &str, files: &[&str]) -> GrantFacts {
    GrantFacts {
        at: Some(glob.into()),
        ..grant(node, atom, files, true)
    }
}

fn universe() -> Vec<String> {
    vec!["fs.read".into(), "fs.write".into(), "net.connect".into()]
}

// frob:tests crates/grimble-bind/src/grants.rs::trust_zones
#[test]
fn every_atom_at_a_broad_glob_is_a_zone_and_overlaps_count_once() {
    let mut all = Vec::new();
    for a in ["fs", "net.connect"] {
        all.push(at(
            "node/t",
            a,
            "\"scripts/**\"",
            &["scripts/a", "scripts/b"],
        ));
        all.push(at(
            "node/u",
            a,
            "\"scripts/**\"",
            &["scripts/b", "scripts/c"],
        ));
    }
    let z = trust_zones(&all, &universe());
    assert_eq!(z.zones.len(), 2, "{z:?}");
    assert_eq!((z.zones[0].node.as_str(), z.zones[0].files), ("node/t", 2));
    assert_eq!(z.files, 3, "scripts/b is counted once");
}

// frob:tests crates/grimble-bind/src/grants.rs::trust_zones
#[test]
fn partial_narrow_scoped_and_empty_inputs_are_not_zones() {
    let f = ["x"];
    // Missing net.connect; a single file glob; an argument-scoped atom; a symbol glob.
    let mut all = vec![
        at("node/a", "fs", "\"t/**\"", &f),
        at("node/b", "fs", "\"one.py\"", &f),
        at("node/b", "net.connect", "\"one.py\"", &f),
        at("node/c", "fs", "\"t/**\"", &f),
        at("node/d", "fs", "\"t/x.py::f**\"", &f),
        at("node/d", "net.connect", "\"t/x.py::f**\"", &f),
        grant("node/e", "fs", &f, true),
        grant("node/e", "net.connect", &f, true),
    ];
    let mut scoped = at("node/c", "net.connect", "\"t/**\"", &f);
    scoped.args = vec!["api.example.com".into()];
    all.push(scoped);
    assert!(trust_zones(&all, &universe()).zones.is_empty());
    assert!(trust_zones(&[], &universe()).zones.is_empty());
    assert!(
        trust_zones(&all, &[]).zones.is_empty(),
        "no atoms means no every-atom claim"
    );
}
