//! The executor's outcome layer: polarity, `unresolved when`, one finding per binding,
//! witnesses and budgets (grl-spec.md 7.0.5).

mod support;

use gob_ir::{Model, NodeId, NodeSpec, Operator, Relation, Truth};
use gob_plan::exec::outcome::{Kind, Outcomes, Reason, outcomes};
use gob_plan::exec::relations::Relations;
use gob_plan::exec::{Doubt, Input};
use gob_plan::plan::{Certainty, CmpOp, Plan, Polarity, Quant};
use support::{Doc, PlanBuilder};

fn func(d: &mut Doc, name: &str, start: u32, kids: &[NodeId]) -> NodeId {
    d.at_range(
        |loc| NodeSpec::new(Operator::unit("function", "impl"), loc).named(name),
        start,
        start + 5,
        kids,
    )
}

fn model(names: &[&str]) -> (Model, Vec<NodeId>) {
    let mut d = Doc::new("a.rs", "rust");
    let fs: Vec<NodeId> = names
        .iter()
        .enumerate()
        .map(|(i, n)| func(&mut d, n, 100 + 10 * u32::try_from(i).unwrap(), &[]))
        .collect();
    let (m, _) = d.root(&fs);
    (m, fs)
}

fn go(plan: &Plan, m: &Model, rels: &Relations) -> Outcomes {
    outcomes(
        plan,
        &Input {
            model: m,
            source: None,
        },
        rels,
    )
    .unwrap()
}

fn calls(edges: &[(NodeId, NodeId, Truth)]) -> Relation {
    let mut r = Relation::new();
    for &(a, b, t) in edges {
        r.insert(a, b, t);
    }
    r
}

/// `find f: function` plus `some t: function where t calls f`, in the given polarity.
fn caller_plan(pol: Polarity) -> (Plan, u16) {
    let mut b = PlanBuilder::new("CALL001", pol);
    let f = b.find("function");
    let q = b.quant(Quant::Some, "function", |b, t| {
        b.verb(t, "calls", f, Certainty::Default)
    });
    b.clause(q);
    b.report(None, f, "called");
    (b.build(), f)
}

// frob:tests crates/gob-plan/src/exec/outcome/mod.rs::outcomes
#[test]
fn a_p_plus_pattern_that_holds_only_through_may_edges_is_unresolved() {
    let (m, fs) = model(&["target", "x"]);
    let (plan, f) = caller_plan(Polarity::Pplus);
    let rels = |t| Relations::new().with_edges("calls", calls(&[(fs[1], fs[0], t)]));

    let may = go(&plan, &m, &rels(Truth::Unknown));
    assert_eq!(may.findings.len(), 1);
    let finding = &may.findings[0];
    assert_eq!(finding.kind, Kind::Unresolved);
    assert_eq!(finding.subject, Some(fs[0]));
    assert!(
        finding
            .reasons
            .iter()
            .any(|r| matches!(r, Reason::Doubt(Doubt::MayEdge { .. })))
    );
    assert_eq!(finding.reasons[0].unresolved().code(), "edge:may");
    // The witness of an Unresolved is the first possible witness.
    assert_eq!(finding.witnesses[0].node, fs[1]);

    let must = go(&plan, &m, &rels(Truth::Yes));
    assert_eq!(must.findings.len(), 1);
    assert_eq!(must.findings[0].kind, Kind::Fire);
    assert!(must.findings[0].reasons.is_empty());
    assert_eq!(must.rows[must.findings[0].row].node(f), Some(fs[0]));

    // No edge at all: clean, so no finding.
    assert!(
        go(
            &plan,
            &m,
            &Relations::new().with_edges("calls", Relation::new())
        )
        .findings
        .is_empty()
    );
}

// frob:tests crates/gob-plan/src/exec/outcome/mod.rs::outcomes
#[test]
fn a_p_minus_rule_fires_when_the_good_thing_is_absent_even_on_may_edges() {
    let (m, fs) = model(&["target", "x"]);
    let (plan, _) = caller_plan(Polarity::Pminus);
    let rels =
        |edges: &[(NodeId, NodeId, Truth)]| Relations::new().with_edges("calls", calls(edges));

    // Absent: both functions are subjects and nothing calls either, so both fire.
    let none = go(&plan, &m, &rels(&[]));
    assert_eq!(none.findings.len(), 2);
    assert!(none.findings.iter().all(|f| f.kind == Kind::Fire));

    // A May edge to the target: it is Unresolved; the other still fires.
    let may = go(&plan, &m, &rels(&[(fs[1], fs[0], Truth::Unknown)]));
    let kinds: Vec<_> = may.findings.iter().map(|f| (f.subject, f.kind)).collect();
    assert_eq!(
        kinds,
        vec![(Some(fs[0]), Kind::Unresolved), (Some(fs[1]), Kind::Fire)]
    );

    // A Must edge: the target is clean and produces no finding.
    let must = go(&plan, &m, &rels(&[(fs[1], fs[0], Truth::Yes)]));
    assert_eq!(must.findings.len(), 1);
    assert_eq!(must.findings[0].subject, Some(fs[1]));
    assert_eq!(must.clean, 1);
}

// frob:tests crates/gob-plan/src/exec/outcome/mod.rs::outcomes
#[test]
fn one_binding_yields_one_finding_from_the_first_yes_report_with_the_first_witness() {
    let (m, fs) = model(&["target", "t1", "t2", "t3"]);
    let rels = Relations::new()
        .with_edges("calls", calls(&[(fs[3], fs[0], Truth::Unknown)]))
        .with_edges(
            "tests",
            calls(&[(fs[2], fs[0], Truth::Yes), (fs[1], fs[0], Truth::Yes)]),
        );
    let mut b = PlanBuilder::new("MANY001", Polarity::Pplus);
    let f = b.find("function");
    let q = b.quant(Quant::Some, "function", |b, t| {
        b.verb(t, "tests", f, Certainty::Default)
    });
    b.clause(q);
    let may = b.quant(Quant::Some, "function", |b, t| {
        b.verb(t, "calls", f, Certainty::Default)
    });
    let yes1 = b.quant(Quant::Some, "function", |b, t| {
        b.verb(t, "tests", f, Certainty::Default)
    });
    let yes2 = b.quant(Quant::Some, "function", |b, t| {
        b.verb(t, "tests", f, Certainty::Default)
    });
    b.report(Some(may), f, "maybe");
    b.report(Some(yes1), f, "first yes");
    b.report(Some(yes2), f, "also yes");
    let plan = b.build();

    let out = go(&plan, &m, &rels);
    assert_eq!(out.findings.len(), 1, "one binding, one finding");
    let finding = &out.findings[0];
    assert_eq!(finding.kind, Kind::Fire);
    assert_eq!(finding.report, 1);
    assert_eq!(finding.notes, vec![0]);
    // fs[1] precedes fs[2] in source order though it was inserted second.
    assert_eq!(finding.witnesses[0].node, fs[1]);
}

// frob:tests crates/gob-plan/src/exec/outcome/mod.rs::outcomes
#[test]
fn unresolved_when_replaces_a_fire_with_its_reason() {
    let (m, _) = model(&["target", "other"]);
    let mut b = PlanBuilder::new("WHEN001", Polarity::Pplus);
    let f = b.find("function");
    let name = b.field(f, "name");
    let lit = b.str_lit("target");
    let c = b.cmp(name, CmpOp::Eq, lit);
    b.clause(c);
    let bad = b.cmp(name, CmpOp::Eq, lit);
    b.unresolved_when(bad, "malformed config entry");
    b.report(None, f, "hit");
    let plan = b.build();
    let out = go(&plan, &m, &Relations::new());
    assert_eq!(out.findings.len(), 1);
    assert_eq!(out.findings[0].kind, Kind::Unresolved);
    assert_eq!(
        out.findings[0].reasons,
        vec![Reason::When("malformed config entry".into())]
    );
}

// frob:tests crates/gob-plan/src/exec/outcome/mod.rs::outcomes
#[test]
fn a_hit_on_an_unread_node_is_unresolved_as_parse_error() {
    let mut d = Doc::new("a.rs", "rust");
    let hole = d.at_range(
        |l| NodeSpec::new(Operator::hole("syntax"), l),
        150,
        152,
        &[],
    );
    let broken = func(&mut d, "broken", 100, &[hole]);
    let (m, _) = d.root(&[broken]);
    let mut b = PlanBuilder::new("PARSE001", Polarity::Pplus);
    let f = b.find("function");
    b.report(None, f, "hit");
    let out = go(&b.build(), &m, &Relations::new());
    assert_eq!(out.findings[0].kind, Kind::Unresolved);
    assert!(out.findings[0].reasons.contains(&Reason::ParseError));
}

// frob:tests crates/gob-plan/src/exec/outcome/mod.rs::outcomes
#[test]
fn a_run_over_its_budget_is_unresolved_budget_not_a_silent_answer() {
    let names: Vec<String> = (0..30).map(|i| format!("f{i}")).collect();
    let strs: Vec<&str> = names.iter().map(String::as_str).collect();
    let (m, _) = model(&strs);
    let (plan, _) = caller_plan(Polarity::Pplus);
    let rels = Relations::new()
        .with_edges("calls", Relation::new())
        .with_step_budget(20);
    let out = go(&plan, &m, &rels);
    assert!(out.truncated);
    assert!(
        out.findings.iter().all(|f| f.kind == Kind::Unresolved
            && f.reasons.iter().any(|r| r.unresolved().code() == "budget")),
        "{:?}",
        out.findings
    );
    assert!(out.rows.len() < 30, "the run stopped enumerating");
}
