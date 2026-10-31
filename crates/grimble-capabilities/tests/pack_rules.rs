//! Unit tests of the pack pass (PACK001 to PACK008).

// frob:ticket 01M3ZX7K3N8AWVBTZ90E0F1YSP

mod common;

use gob_rules::{RequiredReason, Severity};
use grimble_capabilities::pack_rules::{PackHost, UNAVAILABLE_REASON, evaluate, lock_reason};

/// Evaluate a line-format input and return `(rule, message)` pairs.
fn run(text: &str) -> Vec<(String, String)> {
    let inp = common::parse(text);
    evaluate(inp.lock.as_ref(), &inp.packs, &inp.issues)
        .into_iter()
        .map(|f| (f.rule.to_string(), f.message))
        .collect()
}

#[test]
fn pack001_one_finding_per_changed_item_with_reason() {
    // frob:tests crates/grimble-capabilities/src/pack_rules/mod.rs::evaluate
    let r = run("lock a 1.0 t1 k1=d1 k2=d2 k3=d3\nlive a 1.0 t2 k1=dX k3=d3 k4=d4");
    assert_eq!(r.len(), 3, "{r:?}");
    assert!(r.iter().all(|(id, _)| id == "PACK001"));
    assert!(r.iter().any(|(_, m)| m.contains("`k1` changed")));
    assert!(r.iter().any(|(_, m)| m.contains("`k4` added")));
    assert!(r.iter().any(|(_, m)| m.contains("`k2` removed")));
}

#[test]
fn pack001_lock_missing_when_no_lock() {
    // frob:tests crates/grimble-capabilities/src/pack_rules/mod.rs::evaluate
    let r = run("live a 1.0 t1");
    assert_eq!(r.len(), 1);
    assert!(r[0].1.contains("lock-missing"));
}

#[test]
fn pack006_required_unresolved_and_pack001_skips_the_pack() {
    // frob:tests crates/grimble-capabilities/src/pack_rules/mod.rs::evaluate
    let inp =
        common::parse("lock a 1.0 t1 k=d\nlock b 1.0 t1\nunavailable a required\nlive b 1.0 t1");
    let fs = evaluate(inp.lock.as_ref(), &inp.packs, &inp.issues);
    assert_eq!(fs.len(), 1, "{fs:?}");
    let f = &fs[0];
    assert_eq!(f.rule.to_string(), "PACK006");
    assert_eq!(f.severity, Severity::Unresolved);
    assert_eq!(
        f.required,
        Some(RequiredReason::PackUnavailable { pack: "a".into() })
    );
    assert_eq!(
        f.reason.as_ref().map(gob_rules::UnresolvedReason::code),
        Some(UNAVAILABLE_REASON)
    );
}

#[test]
fn pack006_not_required_pack_is_unresolved_only() {
    // frob:tests crates/grimble-capabilities/src/pack_rules/mod.rs::evaluate
    let inp = common::parse("unavailable a");
    let fs = evaluate(None, &inp.packs, &[]);
    assert_eq!(fs.len(), 1);
    assert!(fs[0].required.is_none());
}

#[test]
fn issues_map_to_their_rules_and_severities() {
    // frob:tests crates/grimble-capabilities/src/pack_rules/mod.rs::issue_finding
    let inp = common::parse(
        "issue unknown-atom a x\nissue detector-unavailable a d\nissue duplicate a k\nissue malformed a m\nissue unknown-infer-rule a r\nissue redundant-override a k",
    );
    let fs = evaluate(None, &[], &inp.issues);
    let got: Vec<(String, Severity)> = fs
        .iter()
        .map(|f| (f.rule.to_string(), f.severity))
        .collect();
    assert_eq!(
        got,
        vec![
            ("PACK002".into(), Severity::Error),
            ("PACK003".into(), Severity::Error),
            ("PACK004".into(), Severity::Error),
            ("PACK005".into(), Severity::Error),
            ("PACK007".into(), Severity::Error),
            ("PACK008".into(), Severity::Error),
        ]
    );
}

#[test]
fn lock_reason_names_each_item_change() {
    // frob:tests crates/grimble-capabilities/src/pack_rules/mod.rs::lock_reason
    use gob_packs::lock::{ItemChange, LockFinding};
    let item = |change| LockFinding::Item {
        name: "a".into(),
        key: "k".into(),
        change,
        without_version_bump: true,
    };
    assert_eq!(lock_reason(&item(ItemChange::Added)), "added");
    assert_eq!(lock_reason(&item(ItemChange::Removed)), "removed");
    assert_eq!(lock_reason(&item(ItemChange::Changed)), "changed");
    assert_eq!(
        lock_reason(&LockFinding::LockMissing { name: "a".into() }),
        "lock-missing"
    );
}

/// A host that reports a fixed subject count.
struct Fixed;

impl PackHost for Fixed {
    fn subjects_of(&self, _id: &str) -> usize {
        1
    }
}

#[test]
fn host_reports_subjects() {
    // frob:tests crates/grimble-capabilities/src/pack_rules/host.rs::PackHost.subjects_of
    assert_eq!(Fixed.subjects_of("PACK001"), 1);
}
