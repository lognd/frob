//! Evaluator tests: each polarity, zero-subject and opaque-subject cases, Kleene closure.
#![allow(clippy::many_single_char_names, reason = "terse fixtures")]
#![allow(
    clippy::redundant_closure_for_method_calls,
    reason = "a method path is not higher-ranked over the context lifetime"
)]

mod support;

use std::collections::BTreeSet;

use gob_ir::{
    Answer, AttrValue, EvalConfig, EvalError, Model, NodeId, Observation, Operator, Polarity,
    Relation, RuleOutcome, RuleProgram, ThresholdKind, Truth, Universal, Verdict, reserved,
};
use gob_rules::{RequiredReason, RuleId, Severity, UnresolvedReason};
use support::B;

fn rule(id: &str) -> RuleId {
    id.parse().unwrap()
}

fn run(model: &Model, p: &RuleProgram) -> RuleOutcome {
    p.evaluate(model, &EvalConfig::default()).unwrap()
}

fn is_fn(ctx: &gob_ir::Ctx<'_>, n: NodeId) -> bool {
    ctx.term().node(n).op().is_unit_like() && ctx.term().node(n).name().is_some()
}

fn fn_units(ctx: &gob_ir::Ctx<'_>) -> Answer<Vec<NodeId>> {
    let t = ctx.term();
    Answer::Exact(
        t.units()
            .into_iter()
            .map(|u| u.node)
            .filter(|&n| is_fn(ctx, n))
            .collect(),
    )
}

/// `ok` (documented), `bad` (undocumented, calls `forbidden`), `forbidden`.
fn basic() -> (Model, NodeId, NodeId, NodeId) {
    let mut b = B::new("m.rs", "rust");
    let doc = b.doc("fine");
    let ok = b.unit("function", "ok", &[], &[doc]);
    let call = b.call("forbidden", &[]);
    let bad = b.unit("function", "bad", &[], &[call]);
    let forbidden = b.unit("function", "forbidden", &[], &[]);
    let root = b.file_unit(&[ok, bad, forbidden]);
    (Model::lexical(b.finish(root)), ok, bad, forbidden)
}

fn offenders(
    ctx: &gob_ir::Ctx<'_>,
    subject: NodeId,
    target: NodeId,
) -> (BTreeSet<NodeId>, BTreeSet<NodeId>) {
    let (mut lo, mut hi) = (BTreeSet::new(), BTreeSet::new());
    let Answer::Exact(ds) = ctx.descendants(subject) else {
        return (lo, hi);
    };
    for d in ds {
        if !matches!(
            ctx.term().operator(d),
            Operator::Universal(Universal::Apply { .. })
        ) {
            continue;
        }
        let head = ctx.term().children(d)[0];
        match ctx.resolves_to(head, target) {
            Truth::Yes => {
                lo.insert(d);
                hi.insert(d);
            }
            Truth::Unknown => {
                hi.insert(d);
            }
            Truth::No => {}
        }
    }
    (lo, hi)
}

fn no_forbidden_calls(target: NodeId) -> RuleProgram {
    RuleProgram::new(rule("DENY001"), Polarity::Pplus)
        .message("call to forbidden function")
        .subjects(fn_units)
        .check(move |ctx, s| {
            let (lo, hi) = offenders(ctx, s, target);
            Observation::Set(if lo == hi {
                Answer::Exact(lo)
            } else {
                Answer::Bounds { lo, hi }
            })
        })
}

#[test]
fn p_plus_fires_on_lo_and_certifies_clean_elsewhere() {
    let (m, _ok, bad, forbidden) = basic();
    let out = run(&m, &no_forbidden_calls(forbidden));
    assert_eq!(out.subjects_total, 3);
    assert_eq!(out.subjects_examined, 3);
    let errors: Vec<_> = out
        .findings
        .iter()
        .filter(|f| f.severity == Severity::Error)
        .collect();
    assert_eq!(errors.len(), 1);
    assert!(errors[0].message.contains("m.rs::bad"));
    assert!(
        out.findings
            .iter()
            .all(|f| f.severity != Severity::Unresolved)
    );
    assert_eq!(out.truth(), Truth::No);
    let bad_result = out.results.iter().find(|r| r.subject == bad).unwrap();
    assert!(matches!(bad_result.verdicts[0], Verdict::Violation { .. }));
}

#[test]
fn p_plus_clean_when_no_offender_in_hi() {
    let (m, ..) = basic();
    // Target a node that nobody calls: every subject is certified clean.
    let nobody = m.term().units()[1].node;
    let program = no_forbidden_calls(nobody);
    let out = run(&m, &program);
    assert!(out.findings.is_empty(), "{:?}", out.findings);
    assert_eq!(out.truth(), Truth::Yes);
}

/// A call to `g` made inside a scope where an opaque region may define `g`.
fn opaque_in_cone() -> (Model, NodeId, NodeId) {
    let mut b = B::new("o.py", "python");
    let g = b.unit("function", "g", &[], &[]);
    let spec = b
        .spec(Operator::opaque("dynamic:unresolvable", b"exec(code)"))
        .attr(reserved::MAY_DEFINE, AttrValue::Str("*".into()));
    let opaque = b.add(spec, &[]);
    let call = b.call("g", &[]);
    let user = b.unit("function", "user", &[], &[opaque, call]);
    let root = b.file_unit(&[g, user]);
    (Model::lexical(b.finish(root)), g, user)
}

#[test]
fn p_plus_over_an_opaque_cone_is_unresolved_never_error_or_clean() {
    let (m, g, user) = opaque_in_cone();
    let out = run(&m, &no_forbidden_calls(g));
    assert!(
        out.findings
            .iter()
            .all(|f| f.severity == Severity::Unresolved),
        "{:?}",
        out.findings
    );
    assert!(!out.findings.is_empty());
    let r = out.results.iter().find(|r| r.subject == user).unwrap();
    assert!(matches!(&r.verdicts[0], Verdict::Unresolved { maybe, .. } if maybe.len() == 1));
    assert_eq!(out.truth(), Truth::Unknown);
}

#[test]
fn an_exact_answer_computed_through_poison_is_downgraded_to_unknown() {
    let (m, g, user) = opaque_in_cone();
    // A careless check: counts only certain hits and claims the answer is exact.
    let p = RuleProgram::new(rule("DENY001"), Polarity::Pplus)
        .message("careless")
        .subjects(fn_units)
        .check(move |ctx, s| {
            let (lo, _hi) = offenders(ctx, s, g);
            Observation::Set(Answer::Exact(lo))
        });
    let out = run(&m, &p);
    let r = out.results.iter().find(|r| r.subject == user).unwrap();
    assert!(!r.examined);
    assert!(
        matches!(&r.verdicts[0], Verdict::Unresolved { reason, .. } if matches!(reason, UnresolvedReason::DynamicUnresolvable | UnresolvedReason::EdgeMay | UnresolvedReason::EdgeUnknown))
    );
    assert!(
        out.findings
            .iter()
            .all(|f| f.severity == Severity::Unresolved)
    );
}

#[test]
fn opaque_subject_reports_one_rolled_up_unresolved_with_the_reason_code() {
    let (m, ..) = opaque_in_cone();
    let t = m.term();
    let opaque = t.ids().find(|&n| t.node(n).op().is_opaque()).unwrap();
    let p = RuleProgram::new(rule("DENY001"), Polarity::Pplus)
        .message("forbidden thing")
        .subjects(move |_| Answer::Exact(vec![opaque, opaque]))
        .check(|_, _| unreachable!("opaque subjects are never checked"));
    let out = run(&m, &p);
    assert_eq!(out.subjects_examined, 0);
    assert_eq!(out.findings.len(), 1, "rolled up per rule and artifact");
    let f = &out.findings[0];
    assert_eq!(f.severity, Severity::Unresolved);
    assert_eq!(f.reason, Some(UnresolvedReason::DynamicUnresolvable));
    assert!(f.required.is_none());
}

#[test]
fn annotation_required_opaque_is_required_when_configured() {
    let mut b = B::new("a.py", "python");
    let o = b.node(
        Operator::opaque("annotation-required:signature", b"def f(x): ..."),
        &[],
    );
    let root = b.file_unit(&[o]);
    let m = Model::lexical(b.finish(root));
    let p = RuleProgram::new(rule("COV001"), Polarity::Pminus)
        .message("public symbol has no test")
        .subjects(move |_| Answer::Exact(vec![o]))
        .check(|_, _| Observation::Set(Answer::Exact(BTreeSet::new())));
    let loose = run(&m, &p);
    assert!(loose.findings[0].required.is_none());
    let mut cfg = EvalConfig::default();
    cfg.required_reasons
        .insert("annotation-required:signature".into());
    let strict = p.evaluate(&m, &cfg).unwrap();
    assert_eq!(
        strict.findings[0].reason,
        Some(UnresolvedReason::AnnotationSignature)
    );
    assert_eq!(
        strict.findings[0].required,
        Some(RequiredReason::AnnotationRequired {
            code: "signature".into(),
            public_surface: true
        })
    );
}

#[test]
fn zero_subjects_is_vacuous_unresolved_never_clean() {
    let (m, ..) = basic();
    let p = RuleProgram::new(rule("COV001"), Polarity::Pminus)
        .message("no tests")
        .subjects(|_| Answer::Exact(Vec::new()))
        .check(|_, _| unreachable!());
    let out = run(&m, &p);
    assert_eq!(out.subjects_examined, 0);
    assert_eq!(out.findings.len(), 1);
    assert_eq!(out.findings[0].severity, Severity::Unresolved);
    assert_eq!(out.findings[0].reason, Some(UnresolvedReason::Vacuous));
    assert!(out.findings[0].required.is_none());
    assert_eq!(out.truth(), Truth::Unknown);
}

#[test]
fn must_measure_makes_a_vacuous_rule_required() {
    let (m, ..) = basic();
    let p = RuleProgram::new(rule("NEAT001"), Polarity::Pn)
        .threshold(10, ThresholdKind::Max)
        .must_measure()
        .message("function too long")
        .subjects(|_| Answer::Exact(Vec::new()))
        .check(|_, _| unreachable!());
    let out = run(&m, &p);
    assert_eq!(
        out.findings[0].required,
        Some(RequiredReason::ZeroSubjects {
            rule: "NEAT001".into()
        })
    );
}

#[test]
fn a_wholly_not_applicable_scope_emits_no_findings() {
    let (m, ..) = basic();
    let p = RuleProgram::new(rule("NET001"), Polarity::Pplus)
        .message("net")
        .subjects(|_| Answer::NotApplicable)
        .check(|_, _| unreachable!());
    let out = run(&m, &p);
    assert!(out.not_applicable);
    assert!(out.findings.is_empty());
    let p2 = RuleProgram::new(rule("NET001"), Polarity::Pplus)
        .message("net")
        .subjects(fn_units)
        .check(|_, _| Observation::Set(Answer::NotApplicable));
    let out2 = run(&m, &p2);
    assert!(
        out2.not_applicable,
        "every subject not applicable means the scope is"
    );
    assert!(out2.findings.is_empty());
}

#[test]
fn unknown_subject_set_is_unresolved() {
    let (m, ..) = basic();
    let p = RuleProgram::new(rule("COV001"), Polarity::Pminus)
        .message("tests")
        .subjects(|_| Answer::Unknown)
        .check(|_, _| unreachable!());
    let out = run(&m, &p);
    assert_eq!(out.findings.len(), 1);
    assert_eq!(out.findings[0].severity, Severity::Unresolved);
}

#[test]
fn p_minus_fires_when_no_good_thing_and_is_clean_when_one_exists() {
    let (m, ok, bad, _f) = basic();
    let p = RuleProgram::new(rule("DOC001"), Polarity::Pminus)
        .severity(Severity::Warn)
        .message("undocumented")
        .subjects(fn_units)
        .check(|ctx, s| {
            let Answer::Exact(att) = ctx.attached(s) else { return Observation::Set(Answer::Unknown) };
            let docs = att
                .into_iter()
                .filter(|&a| matches!(ctx.term().operator(a), Operator::Universal(Universal::Attr { name }) if name == "doc"))
                .collect();
            Observation::Set(Answer::Exact(docs))
        });
    let out = run(&m, &p);
    let flagged: Vec<String> = out
        .findings
        .iter()
        .filter(|f| f.severity == Severity::Warn)
        .map(|f| f.message.clone())
        .collect();
    assert_eq!(
        flagged.len(),
        2,
        "bad and forbidden are undocumented: {flagged:?}"
    );
    assert!(flagged.iter().any(|m| m.contains("::bad")));
    let ok_result = out.results.iter().find(|r| r.subject == ok).unwrap();
    assert_eq!(ok_result.verdicts, [Verdict::Clean]);
    let _ = bad;
}

fn fixed(
    polarity: Polarity,
    obs: Observation,
    threshold: Option<(u64, ThresholdKind)>,
) -> RuleOutcome {
    let (m, ..) = basic();
    let root = m.term().root();
    let mut p = RuleProgram::new(rule("TEST001"), polarity)
        .message("fixed")
        .subjects(move |_| Answer::Exact(vec![root]))
        .check(move |_, _| obs.clone());
    if let Some((n, k)) = threshold {
        p = p.threshold(n, k);
    }
    run(&m, &p)
}

fn verdict(out: &RuleOutcome) -> &Verdict {
    &out.results[0].verdicts[0]
}

fn set(items: &[u32]) -> BTreeSet<NodeId> {
    // Node ids are dense arena indices; 0..3 exist in `basic()`.
    let (m, ..) = basic();
    let ids: Vec<NodeId> = m.term().ids().collect();
    items.iter().map(|&i| ids[i as usize]).collect()
}

#[test]
fn p_plus_bounds_table() {
    let exact_empty = fixed(
        Polarity::Pplus,
        Observation::Set(Answer::Exact(set(&[]))),
        None,
    );
    assert_eq!(verdict(&exact_empty), &Verdict::Clean);
    let bounds = Answer::Bounds {
        lo: set(&[0]),
        hi: set(&[0, 1]),
    };
    let both = fixed(Polarity::Pplus, Observation::Set(bounds), None);
    assert_eq!(
        both.results[0].verdicts.len(),
        2,
        "fires on lo and reports hi minus lo"
    );
    assert!(matches!(
        both.results[0].verdicts[0],
        Verdict::Violation { .. }
    ));
    assert!(
        matches!(&both.results[0].verdicts[1], Verdict::Unresolved { maybe, .. } if maybe.len() == 1)
    );
    let maybe_only = Answer::Bounds {
        lo: set(&[]),
        hi: set(&[1]),
    };
    let o = fixed(Polarity::Pplus, Observation::Set(maybe_only), None);
    assert!(matches!(verdict(&o), Verdict::Unresolved { .. }));
    let unknown = fixed(Polarity::Pplus, Observation::Set(Answer::Unknown), None);
    assert!(!unknown.results[0].examined);
}

#[test]
fn p_minus_bounds_table() {
    let none = Answer::Bounds {
        lo: set(&[]),
        hi: set(&[]),
    };
    assert!(matches!(
        verdict(&fixed(Polarity::Pminus, Observation::Set(none), None)),
        Verdict::Violation { .. }
    ));
    let sure = Answer::Bounds {
        lo: set(&[1]),
        hi: set(&[1, 2]),
    };
    assert_eq!(
        verdict(&fixed(Polarity::Pminus, Observation::Set(sure), None)),
        &Verdict::Clean
    );
    let maybe = Answer::Bounds {
        lo: set(&[]),
        hi: set(&[2]),
    };
    assert!(matches!(
        verdict(&fixed(Polarity::Pminus, Observation::Set(maybe), None)),
        Verdict::Unresolved { .. }
    ));
}

#[test]
fn p0_requires_exact_on_both_sides() {
    let eq = Observation::Pair(Answer::Exact("a".into()), Answer::Exact("a".into()));
    assert_eq!(verdict(&fixed(Polarity::P0, eq, None)), &Verdict::Clean);
    let ne = Observation::Pair(Answer::Exact("a".into()), Answer::Exact("b".into()));
    assert!(matches!(
        verdict(&fixed(Polarity::P0, ne, None)),
        Verdict::Violation { .. }
    ));
    let inexact = Observation::Pair(
        Answer::Bounds {
            lo: "a".into(),
            hi: "b".into(),
        },
        Answer::Exact("a".into()),
    );
    let out = fixed(Polarity::P0, inexact, None);
    assert!(matches!(verdict(&out), Verdict::Unresolved { .. }));
    let unknown = Observation::Pair(Answer::Unknown, Answer::Exact("a".into()));
    assert!(!fixed(Polarity::P0, unknown, None).results[0].examined);
}

#[test]
fn pn_max_and_min_thresholds() {
    let max = Some((10, ThresholdKind::Max));
    let min = Some((3, ThresholdKind::Min));
    let c = |a| Observation::Count(a);
    assert!(matches!(
        verdict(&fixed(Polarity::Pn, c(Answer::Exact(11)), max)),
        Verdict::Violation { .. }
    ));
    assert_eq!(
        verdict(&fixed(Polarity::Pn, c(Answer::Exact(10)), max)),
        &Verdict::Clean
    );
    // lo already exceeds N: fires even though the true value is not known exactly.
    assert!(matches!(
        verdict(&fixed(
            Polarity::Pn,
            c(Answer::Bounds { lo: 400, hi: 900 }),
            max
        )),
        Verdict::Violation { .. }
    ));
    assert_eq!(
        verdict(&fixed(
            Polarity::Pn,
            c(Answer::Bounds { lo: 2, hi: 10 }),
            max
        )),
        &Verdict::Clean
    );
    assert!(matches!(
        verdict(&fixed(
            Polarity::Pn,
            c(Answer::Bounds { lo: 2, hi: 11 }),
            max
        )),
        Verdict::Unresolved { .. }
    ));
    assert!(matches!(
        verdict(&fixed(Polarity::Pn, c(Answer::Exact(2)), min)),
        Verdict::Violation { .. }
    ));
    assert!(matches!(
        verdict(&fixed(
            Polarity::Pn,
            c(Answer::Bounds { lo: 0, hi: 2 }),
            min
        )),
        Verdict::Violation { .. }
    ));
    assert_eq!(
        verdict(&fixed(
            Polarity::Pn,
            c(Answer::Bounds { lo: 3, hi: 9 }),
            min
        )),
        &Verdict::Clean
    );
    assert!(matches!(
        verdict(&fixed(
            Polarity::Pn,
            c(Answer::Bounds { lo: 1, hi: 9 }),
            min
        )),
        Verdict::Unresolved { .. }
    ));
}

#[test]
fn pc_reach_table() {
    let r = |lo, hi| Observation::Reach {
        lo,
        hi,
        frontier: Vec::new(),
    };
    assert!(matches!(
        verdict(&fixed(Polarity::Pc, r(true, true), None)),
        Verdict::Violation { .. }
    ));
    assert_eq!(
        verdict(&fixed(Polarity::Pc, r(false, false), None)),
        &Verdict::Clean
    );
    assert!(matches!(
        verdict(&fixed(Polarity::Pc, r(false, true), None)),
        Verdict::Unresolved { .. }
    ));
}

#[test]
fn malformed_programs_are_errors() {
    let (m, ..) = basic();
    let cfg = EvalConfig::default();
    let no_subjects = RuleProgram::new(rule("TEST001"), Polarity::Pplus)
        .check(|_, _| Observation::Set(Answer::Unknown));
    assert_eq!(
        no_subjects.evaluate(&m, &cfg).unwrap_err(),
        EvalError::NoSubjects
    );
    let no_check = RuleProgram::new(rule("TEST001"), Polarity::Pplus).subjects(|_| Answer::Unknown);
    assert_eq!(no_check.evaluate(&m, &cfg).unwrap_err(), EvalError::NoCheck);
    let no_threshold = RuleProgram::new(rule("TEST001"), Polarity::Pn)
        .subjects(|_| Answer::Unknown)
        .check(|_, _| Observation::Count(Answer::Unknown));
    assert_eq!(
        no_threshold.evaluate(&m, &cfg).unwrap_err(),
        EvalError::NoThreshold
    );
    let root = m.term().root();
    let mismatch = RuleProgram::new(rule("TEST001"), Polarity::Pc)
        .subjects(move |_| Answer::Exact(vec![root]))
        .check(|_, _| Observation::Count(Answer::Exact(1)));
    assert!(matches!(
        mismatch.evaluate(&m, &cfg).unwrap_err(),
        EvalError::Mismatch { .. }
    ));
}

/// `a <-> b` with certain edges; `c -> d` certain and `d -> c` only possible when `may_cycle`.
fn calls_model(may_cycle: bool, must_cycle: bool) -> Model {
    let mut b = B::new("c.rs", "rust");
    let mut kids = Vec::new();
    let ca = b.call("b", &[]);
    let a = b.unit("function", "a", &[], &[ca]);
    let cb = if must_cycle {
        b.call("a", &[])
    } else {
        b.lit("done")
    };
    let bb = b.unit("function", "b", &[], &[cb]);
    kids.extend([a, bb]);
    if may_cycle {
        let cc = b.call("d", &[]);
        let c = b.unit("function", "c", &[], &[cc]);
        let spec = b.spec(Operator::opaque("dynamic:unresolvable", b"x")).attr(
            reserved::MAY_DEFINE,
            AttrValue::List(vec![AttrValue::Str("c".into())]),
        );
        let opaque = b.add(spec, &[]);
        let cd = b.call("c", &[]);
        let d = b.unit("function", "d", &[], &[opaque, cd]);
        kids.extend([c, d]);
    }
    let root = b.file_unit(&kids);
    Model::lexical(b.finish(root))
}

fn cycle_rule() -> RuleProgram {
    RuleProgram::new(rule("CYCLE001"), Polarity::Pc)
        .message("call cycle")
        .subjects(fn_units)
        .check(|ctx, s| {
            let reach = ctx.rel_calls().closure();
            let frontier = ctx.poison().into_iter().map(|p| p.node).collect();
            Observation::reach(reach.get(s, s), frontier)
        })
}

fn named(out: &RuleOutcome, m: &Model, name: &str) -> Vec<Verdict> {
    let t = m.term();
    let n = t
        .units()
        .into_iter()
        .find(|u| u.symref.to_string() == format!("c.rs::{name}"))
        .unwrap()
        .node;
    out.results
        .iter()
        .find(|r| r.subject == n)
        .unwrap()
        .verdicts
        .clone()
}

#[test]
fn pc_must_cycle_fires_and_acyclic_is_clean() {
    let m = calls_model(false, true);
    let out = run(&m, &cycle_rule());
    let errors = out
        .findings
        .iter()
        .filter(|f| f.severity == Severity::Error)
        .count();
    assert_eq!(errors, 2);
    let acyclic = calls_model(false, false);
    let out = run(&acyclic, &cycle_rule());
    assert!(out.findings.is_empty(), "{:?}", out.findings);
    assert_eq!(out.truth(), Truth::Yes);
}

#[test]
fn pc_may_cycle_is_unresolved_but_a_must_cycle_elsewhere_still_fires() {
    let m = calls_model(true, true);
    let out = run(&m, &cycle_rule());
    assert!(matches!(named(&out, &m, "a")[0], Verdict::Violation { .. }));
    assert!(matches!(
        named(&out, &m, "c")[0],
        Verdict::Unresolved { .. }
    ));
    assert!(matches!(
        named(&out, &m, "d")[0],
        Verdict::Unresolved { .. }
    ));
    let errors = out
        .findings
        .iter()
        .filter(|f| f.severity == Severity::Error)
        .count();
    assert_eq!(errors, 2, "only the certain cycle fires");
    assert!(
        out.findings
            .iter()
            .any(|f| f.severity == Severity::Unresolved)
    );
}

#[test]
fn strata_derive_relations_read_by_later_strata_and_checks() {
    let m = calls_model(false, true);
    let p = RuleProgram::new(rule("REACH001"), Polarity::Pc)
        .message("a reaches itself")
        .stratum("calls", |ctx| ctx.rel_calls())
        .stratum("reach", |ctx| {
            ctx.derived("calls").expect("earlier stratum").closure()
        })
        .subjects(fn_units)
        .check(|ctx, s| {
            let reach = ctx.derived("reach").expect("derived");
            Observation::reach(ctx.holds(&reach, s, s), Vec::new())
        });
    let out = run(&m, &p);
    assert_eq!(out.findings.len(), 2);
}

#[test]
fn relation_closure_is_a_kleene_least_fixpoint() {
    let (m, ..) = basic();
    let ids: Vec<NodeId> = m.term().ids().collect();
    let (a, b, c) = (ids[0], ids[1], ids[2]);
    let mut r = Relation::new();
    r.insert(a, b, Truth::Yes);
    r.insert(b, c, Truth::Unknown);
    r.insert(c, a, Truth::Yes);
    let cl = r.closure();
    assert_eq!(cl.get(a, b), Truth::Yes);
    assert_eq!(cl.get(a, c), Truth::Unknown);
    assert_eq!(cl.get(a, a), Truth::Unknown);
    assert_eq!(cl.get(c, b), Truth::Yes);
    assert_eq!(r.compose(&r).get(a, c), Truth::Unknown);
    assert_eq!(r.union(&cl).get(a, a), Truth::Unknown);
    assert_eq!(cl.get(b, b), Truth::Unknown);
}

#[test]
fn kleene_connectives() {
    use Truth::{No, Unknown, Yes};
    assert_eq!(Yes & Unknown, Unknown);
    assert_eq!(No & Unknown, No);
    assert_eq!(Yes | Unknown, Yes);
    assert_eq!(No | Unknown, Unknown);
    assert_eq!(!Unknown, Unknown);
    assert_eq!(Truth::all([Yes, Yes]), Yes);
    assert_eq!(Truth::all([Yes, Unknown, No]), No);
    assert_eq!(Truth::any([No, Unknown]), Unknown);
    assert_eq!(Truth::any(std::iter::empty()), No);
    assert_eq!(Truth::from(true), Yes);
}

// frob:tests crates/gob-ir/src/eval/program.rs::RuleOutcome.into_report
#[test]
fn an_outcome_converts_into_a_rule_report_with_its_accounting() {
    let (m, _ok, _bad, forbidden) = basic();
    let out = run(&m, &no_forbidden_calls(forbidden));
    let (total, examined, n) = (
        out.subjects_total,
        out.subjects_examined,
        out.findings.len(),
    );
    let report = out.into_report();
    assert_eq!(report.subjects_total, total);
    assert_eq!(report.subjects_examined, examined);
    assert_eq!(report.findings.len(), n);
    assert!(report.not_applicable.is_none());
    assert!(!report.is_certified_clean());
}

#[test]
fn a_hole_and_a_may_edge_carry_their_typed_reasons_on_the_finding() {
    let (m, g, _user) = opaque_in_cone();
    let out = run(&m, &no_forbidden_calls(g));
    assert!(
        out.findings.iter().all(|f| f.reason.is_some()),
        "every Unresolved carries a typed reason: {:?}",
        out.findings
    );
}
