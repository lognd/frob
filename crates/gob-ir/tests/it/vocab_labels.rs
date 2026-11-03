//! Small vocabulary helpers: rule-id parts, fingerprint hex, applicability labels, error-set claims.
// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use std::collections::BTreeSet;

use gob_ir::error_flow::ErrorSet;
use gob_ir::vocab::finding::Fingerprint;
use gob_ir::vocab::id::RuleId;
use gob_ir::vocab::severity::Applicability;

// frob:tests crates/gob-ir/src/vocab/id.rs::RuleId.family
// frob:tests crates/gob-ir/src/vocab/id.rs::RuleId.number
#[test]
fn rule_id_splits_into_family_and_number() {
    let id: RuleId = "COV001".parse().expect("rule id");
    assert_eq!(id.family(), "COV");
    assert_eq!(id.number(), 1);
}

// frob:tests crates/gob-ir/src/vocab/finding.rs::Fingerprint.to_hex
#[test]
fn fingerprint_hex_is_64_lowercase_digits_and_displayed() {
    let id: RuleId = "COV001".parse().expect("rule id");
    let fp = Fingerprint::compute(&id, "a.rs::f", "m");
    let hex = fp.to_hex();
    assert_eq!(hex.len(), 64);
    assert!(
        hex.bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    );
    assert_eq!(fp.to_string(), hex);
}

// frob:tests crates/gob-ir/src/vocab/severity.rs::Applicability.label
#[test]
fn applicability_labels_are_kebab_case() {
    assert_eq!(Applicability::Machine.label(), "machine");
    assert_eq!(Applicability::MaybeIncorrect.label(), "maybe-incorrect");
    assert_eq!(Applicability::HasPlaceholders.label(), "has-placeholders");
    assert_eq!(Applicability::Manual.label(), "manual");
}

// frob:tests crates/gob-ir/src/error_flow.rs::ErrorSet.within
#[test]
fn error_set_is_within_a_claim_only_when_closed_and_subset() {
    let claim: BTreeSet<String> = ["A", "B"].iter().map(|s| (*s).to_owned()).collect();
    let mut set = ErrorSet {
        members: ["A"].iter().map(|s| (*s).to_owned()).collect(),
        open: false,
    };
    assert!(set.within(&claim));
    set.open = true;
    assert!(!set.within(&claim));
    set.open = false;
    set.members.insert("C".to_owned());
    assert!(!set.within(&claim));
}
