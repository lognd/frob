//! The outcome layer's remaining gaps: not-applicable bindings, `certainly` assumptions and the
//! typed reasons of budget and partial subjects (grl-spec.md 7.0.4, 7.0.5 and 7.0.7).
//!
//! frob:ticket 01M4HGGN9JCP9C1F7PQSVFPB29

mod support;

use gob_caps::{Capability, Lang};
use gob_ir::{Model, NodeId, NodeSpec, Operator, Relation, Truth};
use gob_plan::exec::outcome::{Applicability, Kind, Outcomes, Reason, outcomes, outcomes_in};
use gob_plan::exec::relations::Relations;
use gob_plan::exec::{Doubt, Input};
use gob_plan::plan::{Certainty, Plan, Polarity, Quant};
use gob_rules::UnresolvedReason;
use support::{Doc, PlanBuilder};

fn model(names: &[&str]) -> (Model, Vec<NodeId>) {
    let mut d = Doc::new("a.rs", "rust");
    let fs: Vec<NodeId> = names
        .iter()
        .enumerate()
        .map(|(i, n)| {
            let start = 100 + 10 * u32::try_from(i).unwrap();
            d.at_range(
                |loc| NodeSpec::new(Operator::unit("function", "impl"), loc).named(n),
                start,
                start + 5,
                &[],
            )
        })
        .collect();
    let (m, _) = d.root(&fs);
    (m, fs)
}

fn input(m: &Model) -> Input<'_> {
    Input {
        model: m,
        source: None,
    }
}

/// `find f: function` with the good thing `some t: function where t calls f` at `certainty`.
fn caller_plan(pol: Polarity, certainty: Certainty) -> Plan {
    let mut b = PlanBuilder::new("CALL002", pol);
    let f = b.find("function");
    b.end_subjects();
    let q = b.quant(Quant::Some, "function", |b, t| {
        b.verb(t, "calls", f, certainty)
    });
    b.clause(q);
    b.report(None, f, "uncalled");
    b.build()
}

fn calls(edges: &[(NodeId, NodeId, Truth)]) -> Relation {
    let mut r = Relation::new();
    for &(a, b, t) in edges {
        r.insert(a, b, t);
    }
    r
}

// frob:tests crates/gob-plan/src/exec/outcome/mod.rs::outcomes_in
#[test]
fn a_not_applicable_cell_yields_no_finding_no_clean_and_no_unresolved() {
    let (m, fs) = model(&["target", "x"]);
    let plan = caller_plan(Polarity::Pminus, Certainty::Default);
    let rels = Relations::new().with_edges("calls", calls(&[(fs[1], fs[0], Truth::Unknown)]));

    let needs = [Capability::ApplyTargets];
    let na = outcomes_in(&plan, &input(&m), &rels, Lang::Binary, &needs).unwrap();
    assert_eq!(
        na.applicability,
        Applicability::NotApplicable {
            capability: Capability::ApplyTargets
        }
    );
    assert!(na.findings.is_empty() && na.rows.is_empty());
    assert_eq!(na.clean, 0);

    // The same plan on a language that provides the capability runs and finds things.
    let ok = outcomes_in(&plan, &input(&m), &rels, Lang::Rust, &needs).unwrap();
    assert_eq!(ok.applicability, Applicability::Applicable);
    assert!(!ok.findings.is_empty());

    // No needed capability is never not applicable.
    let none = outcomes_in(&plan, &input(&m), &rels, Lang::Binary, &[]).unwrap();
    assert_eq!(none.applicability, Applicability::Applicable);
}

// frob:tests crates/gob-plan/src/exec/outcome/mod.rs::outcomes
// frob:tests crates/gob-plan/src/exec/outcome/mod.rs::Finding.is_conditional
// frob:tests crates/gob-plan/src/exec/outcome/assume.rs::Assumption.code
#[test]
fn a_fire_resting_on_certainly_is_conditional_with_an_assumed_reason() {
    let (m, fs) = model(&["target", "x"]);
    // x calls target only through a May edge; nothing calls x.
    let rels = Relations::new().with_edges("calls", calls(&[(fs[1], fs[0], Truth::Unknown)]));

    let certain = outcomes(
        &caller_plan(Polarity::Pminus, Certainty::Certainly),
        &input(&m),
        &rels,
    )
    .unwrap();
    let by_subject = |o: &Outcomes, n: NodeId| {
        o.findings
            .iter()
            .find(|f| f.subject == Some(n))
            .cloned()
            .expect("a finding for the subject")
    };
    // target: the May edge collapses to No, so the rule fires, but only by assumption.
    let target = by_subject(&certain, fs[0]);
    assert_eq!(target.kind, Kind::Fire);
    assert!(target.is_conditional());
    let codes: Vec<String> = target
        .assumptions
        .iter()
        .map(gob_plan::exec::outcome::Assumption::code)
        .collect();
    assert_eq!(codes.len(), 1);
    assert!(codes[0].starts_with("assumed:certainly@"), "{codes:?}");
    assert_eq!(
        target.assumptions[0].unresolved(),
        UnresolvedReason::Opaque(codes[0].clone())
    );
    // x: nothing calls it even with May edges read as present, so the fire is unconditional.
    let x = by_subject(&certain, fs[1]);
    assert_eq!(x.kind, Kind::Fire);
    assert!(!x.is_conditional());

    // Without the keyword the same binding is Unresolved, not a fire.
    let plain = outcomes(
        &caller_plan(Polarity::Pminus, Certainty::Default),
        &input(&m),
        &rels,
    )
    .unwrap();
    assert_eq!(by_subject(&plain, fs[0]).kind, Kind::Unresolved);
    assert!(plain.findings.iter().all(|f| f.assumptions.is_empty()));
}

// frob:tests crates/gob-plan/src/exec/outcome/reason.rs::Reason.unresolved
#[test]
fn budget_and_partial_subjects_map_to_their_dedicated_variants() {
    let (_, fs) = model(&["f"]);
    let from = fs[0];
    assert_eq!(
        Reason::Doubt(Doubt::Budget { from, within: 3 }).unresolved(),
        UnresolvedReason::Budget
    );
    assert_eq!(
        Reason::Doubt(Doubt::StepBudget).unresolved(),
        UnresolvedReason::Budget
    );
    assert_eq!(Reason::Hidden.unresolved(), UnresolvedReason::Partial);
    assert_eq!(
        Reason::Doubt(Doubt::Hidden).unresolved(),
        UnresolvedReason::Partial
    );
    assert_eq!(Reason::ParseError.unresolved(), UnresolvedReason::Hole);
    for r in [Reason::Doubt(Doubt::StepBudget), Reason::Hidden] {
        assert!(!matches!(r.unresolved(), UnresolvedReason::Opaque(_)));
    }
}
