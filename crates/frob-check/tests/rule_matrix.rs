//! Every Universal frob rule fills the language matrix, with expectations derived from its needs.

// frob:ticket 01M48Q4DMNMQEYQNWPK42DZ0RZ

// The rule crates are linked only for their inventory registrations.
use frob_check as _;

use gob_check::SubjectStatus;
use gob_check::applicability::{Applies, derive_cell, temporary_applies};

use gob_mdtest::matrix::Derived;
use gob_rules::Registry;

/// The `frob` rules whose declared applicability is Universal.
fn universal_rules() -> Vec<String> {
    Registry::global()
        .iter()
        .filter(|m| m.product == "frob")
        .filter(|m| matches!(temporary_applies(m), Applies::Universal { .. }))
        .map(|m| m.id.to_owned())
        .collect()
}

/// The derived class of `rule` in `cell`, from its declared `applies` and the capability matrix.
fn derive(rule: &str, cell: &str) -> Option<Derived> {
    let meta = Registry::global().iter().find(|m| m.id == rule)?;
    Some(match derive_cell(&temporary_applies(meta), cell)? {
        SubjectStatus::Examine => Derived::Examine,
        SubjectStatus::Unresolved(_) => Derived::Unresolved,
        SubjectStatus::NotApplicable(_) => Derived::NotApplicable,
    })
}

// frob:tests crates/gob-mdtest/src/matrix.rs::assert_matrix
#[test]
fn every_universal_frob_rule_fills_the_matrix() {
    let rules = universal_rules();
    assert!(!rules.is_empty(), "no Universal frob rules registered");
    gob_mdtest::matrix::assert_matrix(env!("CARGO_MANIFEST_DIR"), "frob", &rules, &derive);
}
