//! Impl outcome-map planning: non-Exact error facts are Unresolved, a claim resolves conditionally.

// frob:ticket 01M68WWE14NTX7QGN0T0W79F8B

use std::collections::BTreeSet;

use gob_ir::error_flow::{
    ErrorFacts, ErrorResolution, OutcomeMapClaim, RustErrorType, noexcept_claim,
};
use gob_rules::Severity;
use grimble_bind::outcome::{OUTCOME_RULE, plan_outcome_map};

const IMPL: &str = "impl/S.sc.o.step";

fn claim() -> OutcomeMapClaim {
    OutcomeMapClaim {
        label: "outcomes@pay.grmb:3".to_owned(),
        errors: BTreeSet::from(["PayError::Declined".to_owned()]),
    }
}

#[test]
// frob:tests crates/grimble-bind/src/outcome.rs::plan_outcome_map
fn non_exact_facts_are_reported_unresolved() {
    let facts = ErrorFacts::typescript(&["pay.ts:4"]);
    let plan = plan_outcome_map(IMPL, facts, None);
    assert!(matches!(plan.resolution, ErrorResolution::Unresolved(_)));
    assert_eq!(plan.findings.len(), 1);
    let f = &plan.findings[0];
    assert_eq!(f.rule, OUTCOME_RULE);
    assert_eq!(f.severity, Severity::Unresolved);
    assert_eq!(f.anchor, IMPL);
    assert!(f.reason.is_some());
    assert!(f.message.contains("ts:throw:pay.ts:4"), "{}", f.message);
}

#[test]
// frob:tests crates/grimble-bind/src/outcome.rs::plan_outcome_map
fn outcome_map_claim_resolves_conditionally() {
    let facts = ErrorFacts::rust(&RustErrorType::Erased {
        name: "anyhow::Error".to_owned(),
    });
    let plan = plan_outcome_map(IMPL, facts, Some(&claim()));
    assert_eq!(
        plan.resolution,
        ErrorResolution::Conditional(vec!["outcomes@pay.grmb:3".to_owned()])
    );
    assert!(plan.findings.is_empty());
}

#[test]
// frob:tests crates/grimble-bind/src/outcome.rs::plan_outcome_map
fn exact_facts_stay_closed_with_or_without_a_claim() {
    let ty = RustErrorType::ClosedEnum {
        name: "PayError".to_owned(),
        variants: vec!["Declined".to_owned()],
    };
    for c in [None, Some(noexcept_claim("noexcept@x:1"))] {
        let plan = plan_outcome_map(IMPL, ErrorFacts::rust(&ty), c.as_ref());
        assert_eq!(plan.resolution, ErrorResolution::Closed);
        assert!(plan.findings.is_empty());
    }
}
