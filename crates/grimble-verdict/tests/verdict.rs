//! The shared verdict type: constructors and conversion to the pipeline finding.
// frob:ticket 01M5F0111KG4GZSMSS7PX9D61N

use gob_rules::{Severity, UnresolvedReason};
use gob_text::FileInterner;
use grimble_verdict::Verdict;

/// `fire` builds a resolved verdict and `into_finding` keeps its rule, severity and anchor.
// frob:tests crates/grimble-verdict/src/lib.rs::Verdict.fire
// frob:tests crates/grimble-verdict/src/lib.rs::Verdict.into_finding
#[test]
fn resolved_verdict_converts_to_a_finding() {
    let v = Verdict::fire(
        "CYCLE001",
        Severity::Error,
        ("a.rs", (3, 9)),
        "cycle".to_owned(),
        "a".to_owned(),
    );
    assert_eq!(v.reason, None);
    let mut files = FileInterner::new();
    let f = v.into_finding(&mut files).expect("valid rule id");
    assert_eq!(f.rule.as_str(), "CYCLE001");
    assert_eq!(f.severity, Severity::Error);
}

/// An unresolved verdict carries its reason and severity through conversion; a bad id yields `None`.
// frob:tests crates/grimble-verdict/src/lib.rs::Verdict.unresolved
#[test]
fn unresolved_verdict_keeps_its_reason_and_bad_ids_are_dropped() {
    let v = Verdict::unresolved(
        "DEAD001",
        UnresolvedReason::ParseFailed,
        ("b.rs", (0, 0)),
        "m".to_owned(),
        "b".to_owned(),
    );
    assert_eq!(v.severity, Severity::Unresolved);
    assert_eq!(v.reason, Some(UnresolvedReason::ParseFailed));
    let mut files = FileInterner::new();
    assert!(v.clone().into_finding(&mut files).is_some());
    let bad = Verdict {
        rule: "not a rule",
        ..v
    };
    assert!(bad.into_finding(&mut files).is_none());
}
