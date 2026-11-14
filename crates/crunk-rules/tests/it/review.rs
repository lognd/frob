//! The human review judgment: stale naming, allow-list, signatures and rejection.

// frob:ticket 01M4CXSM408E7A05DWKENDB7V4

use std::collections::BTreeMap;

use crunk_rules::review::{AckSignature, ReviewStatus, Subject, changed_inputs, judge};
use crunk_spec::table::{ReviewConfig, Reviewer};
use gob_lock::{ReviewEntry, ReviewVerdict};

fn subject(bg: &str) -> Subject {
    Subject {
        id: "screen/home/default".to_owned(),
        screen: "home".to_owned(),
        inputs: BTreeMap::from([
            ("token:--color-bg".to_owned(), bg.to_owned()),
            ("source:src/home.tsx".to_owned(), "s1".to_owned()),
        ]),
    }
}

fn entry(of: &Subject, reviewer: &str, verdict: ReviewVerdict) -> ReviewEntry {
    ReviewEntry {
        digest: of.digest(),
        verdict,
        reviewer: reviewer.to_owned(),
        at: "2026-10-13T00:00:00Z".to_owned(),
        note: None,
        render: None,
        non_interactive: false,
        inputs: of.inputs.clone(),
    }
}

fn policy(require_signed: bool) -> ReviewConfig {
    ReviewConfig {
        reviewers: vec![Reviewer {
            id: "a@x.io".to_owned(),
            keys: vec!["ABCD1234".to_owned()],
        }],
        require_signed,
    }
}

// frob:tests crates/crunk-rules/src/review.rs::judge
#[test]
fn a_changed_token_makes_the_review_stale_and_is_named() {
    let e = entry(&subject("old"), "A <a@x.io>", ReviewVerdict::Approved);
    let f = judge(&subject("new"), Some(&e), &ReviewConfig::default(), None);
    assert_eq!(
        f.status,
        ReviewStatus::Stale(vec!["token:--color-bg".to_owned()])
    );
    assert!(f.message.contains("`home`") && f.message.contains("token:--color-bg"));
    let same = judge(&subject("old"), Some(&e), &ReviewConfig::default(), None);
    assert_eq!(same.status, ReviewStatus::Current);
}

// frob:tests crates/crunk-rules/src/review.rs::changed_inputs
#[test]
fn changed_inputs_lists_added_removed_and_changed() {
    let a = BTreeMap::from([
        ("x".to_owned(), "1".to_owned()),
        ("y".to_owned(), "1".to_owned()),
    ]);
    let b = BTreeMap::from([
        ("y".to_owned(), "2".to_owned()),
        ("z".to_owned(), "1".to_owned()),
    ]);
    assert_eq!(changed_inputs(&a, &b), ["x", "y", "z"]);
}

// frob:tests crates/crunk-rules/src/review.rs::judge
#[test]
fn signatures_and_the_allow_list_are_enforced() {
    let s = subject("new");
    let e = entry(&s, "A <a@x.io>", ReviewVerdict::Approved);
    let good = AckSignature::Good("0000ABCD1234".to_owned());
    assert_eq!(
        judge(&s, Some(&e), &policy(true), Some(&good)).status,
        ReviewStatus::Current
    );
    let other = AckSignature::Good("FFFF9999".to_owned());
    assert!(matches!(
        judge(&s, Some(&e), &policy(true), Some(&other)).status,
        ReviewStatus::Unsigned(_)
    ));
    let none = AckSignature::Unsigned("not signed".to_owned());
    assert!(matches!(
        judge(&s, Some(&e), &policy(true), Some(&none)).status,
        ReviewStatus::Unsigned(_)
    ));
    let stranger = entry(&s, "M <m@x.io>", ReviewVerdict::Approved);
    assert!(matches!(
        judge(&s, Some(&stranger), &policy(false), None).status,
        ReviewStatus::Unlisted(_)
    ));
}

// frob:tests crates/crunk-rules/src/review.rs::judge
#[test]
fn a_current_rejection_is_rejected_and_a_missing_entry_is_missing() {
    let s = subject("new");
    let e = entry(&s, "A <a@x.io>", ReviewVerdict::Rejected);
    assert!(matches!(
        judge(&s, Some(&e), &ReviewConfig::default(), None).status,
        ReviewStatus::Rejected(_)
    ));
    assert_eq!(
        judge(&s, None, &ReviewConfig::default(), None).status,
        ReviewStatus::Missing
    );
}
