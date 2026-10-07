//! The typed Unresolved reason and the per-rule report (D106).

use gob_rules::{Finding, RuleReport, Severity, UnresolvedReason};

const TABLE: &[(&str, UnresolvedReason)] = &[
    (
        "annotation-required:signature",
        UnresolvedReason::AnnotationSignature,
    ),
    (
        "annotation-required:effects",
        UnresolvedReason::AnnotationEffects,
    ),
    (
        "dynamic:unresolvable",
        UnresolvedReason::DynamicUnresolvable,
    ),
    ("dynamic:string-code", UnresolvedReason::DynamicStringCode),
    ("expansion:budget", UnresolvedReason::ExpansionBudget),
    (
        "normalization:unverified",
        UnresolvedReason::NormalizationUnverified,
    ),
    ("order:unrecorded", UnresolvedReason::OrderUnrecorded),
    ("hole", UnresolvedReason::Hole),
    ("edge:may", UnresolvedReason::EdgeMay),
    ("edge:unknown", UnresolvedReason::EdgeUnknown),
    ("vacuous", UnresolvedReason::Vacuous),
    ("fidelity", UnresolvedReason::Fidelity),
    ("parse-failed", UnresolvedReason::ParseFailed),
    ("partial", UnresolvedReason::Partial),
];

// frob:tests crates/gob-rules/src/unresolved.rs::UnresolvedReason
#[test]
fn every_code_round_trips_through_the_typed_reason_and_its_json_string() {
    for (code, reason) in TABLE {
        assert_eq!(&UnresolvedReason::from_code(code), reason, "{code}");
        assert_eq!(reason.code(), *code);
        let json = serde_json::to_string(reason).unwrap();
        assert_eq!(json, format!("\"{code}\""));
        let back: UnresolvedReason = serde_json::from_str(&json).unwrap();
        assert_eq!(&back, reason);
    }
}

#[test]
fn an_unlisted_code_is_opaque_and_keeps_its_code() {
    let r = UnresolvedReason::from_code("opaque:shell");
    assert_eq!(r, UnresolvedReason::Opaque("opaque:shell".into()));
    assert_eq!(r.code(), "opaque:shell");
    assert_eq!(
        UnresolvedReason::from_code("unknown"),
        UnresolvedReason::EdgeUnknown
    );
}

// frob:tests crates/gob-rules/src/finding.rs::Finding.with_reason
#[test]
fn a_finding_carries_its_reason_without_reading_the_message() {
    let f = Finding::new(
        "COV001".parse().unwrap(),
        Severity::Unresolved,
        None,
        "vacuous in words only",
        "x",
    );
    assert_eq!(f.reason, None);
    let f = f.with_reason(UnresolvedReason::Fidelity);
    assert_eq!(f.reason, Some(UnresolvedReason::Fidelity));
}

// frob:tests crates/gob-rules/src/unresolved.rs::RuleReport
#[test]
fn a_rule_report_is_clean_only_when_applied_examined_and_silent() {
    let id = || "COV001".parse().unwrap();
    assert!(RuleReport::new(id(), 2, 2, None, Vec::new()).is_certified_clean());
    assert!(!RuleReport::new(id(), 0, 0, None, Vec::new()).is_certified_clean());
    assert!(!RuleReport::new(id(), 0, 0, Some("binary".into()), Vec::new()).is_certified_clean());
    let u = Finding::new(id(), Severity::Unresolved, None, "m", "x")
        .with_reason(UnresolvedReason::Vacuous);
    let r = RuleReport::new(id(), 1, 0, None, vec![u]);
    assert!(!r.is_certified_clean());
    assert_eq!(r.unresolved().count(), 1);
}
