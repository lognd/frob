//! Property test for the rule polarity mapping (Pc, P+, P-, P0, Pn) against Kleene verdicts.
//!
//! A random structure of functions is built, some calling a target and some holding an opaque
//! cone that may define anything (so a call may be shadowed and a hidden call may exist). A
//! `RuleProgram` of each polarity is interpreted over it, and every completion of the unknown
//! part is enumerated: each `Violation` and each certified `Clean` must hold in every completion
//! (soundness, including the downgrade of a careless `Exact` answer computed through poison), and
//! a structure with no opaque cone must never produce an `Unresolved` verdict (exactness).
// frob:ticket 01M4D6NVK70SB76M5EQ3RECX85
#![allow(
    clippy::redundant_closure_for_method_calls,
    reason = "a method path is not higher-ranked over the context lifetime"
)]

mod support;

use std::collections::BTreeSet;

use gob_ir::{
    Answer, AttrValue, Ctx, EvalConfig, Model, NodeId, Observation, Operator, Polarity,
    RuleProgram, ThresholdKind, Truth, Universal, Verdict, reserved,
};
use gob_rules::RuleId;
use proptest::prelude::*;
use support::B;

const MAX_SUBJECTS: usize = 4;

/// One generated function: whether it calls the target and whether it holds an opaque cone.
#[derive(Debug, Clone, Copy)]
struct Spec {
    calls: bool,
    dynamic: bool,
}

/// The built structure: the model, the target and, per subject, its node and call node.
struct Built {
    model: Model,
    target: NodeId,
    subjects: Vec<(NodeId, Option<NodeId>)>,
}

fn build(specs: &[Spec]) -> Built {
    let mut b = B::new("p.py", "python");
    let target = b.unit("function", "g", &[], &[]);
    let mut units = vec![target];
    let mut subjects = Vec::new();
    for (i, s) in specs.iter().enumerate() {
        let mut kids = Vec::new();
        if s.dynamic {
            let spec = b
                .spec(Operator::opaque("dynamic:unresolvable", b"exec(code)"))
                .attr(reserved::MAY_DEFINE, AttrValue::Str("*".into()));
            kids.push(b.add(spec, &[]));
        }
        let call = s.calls.then(|| b.call("g", &[]));
        kids.extend(call);
        let unit = b.unit("function", &format!("f{i}"), &[], &kids);
        units.push(unit);
        subjects.push((unit, call));
    }
    let root = b.file_unit(&units);
    Built {
        model: Model::lexical(b.finish(root)),
        target,
        subjects,
    }
}

/// The certain and possible calls of `subject` to `target`.
fn offenders(
    ctx: &Ctx<'_>,
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

/// A rule of `polarity` over the subjects named `f*`; `careless` claims `Exact` even from bounds.
fn program(
    built: &Built,
    polarity: Polarity,
    careless: bool,
    threshold: (u64, ThresholdKind),
) -> RuleProgram {
    let target = built.target;
    let subjects: Vec<NodeId> = built.subjects.iter().map(|(u, _)| *u).collect();
    let id: RuleId = "PROP001".parse().expect("rule id");
    let mut p = RuleProgram::new(id, polarity)
        .message("property")
        .subjects(move |_| Answer::Exact(subjects.clone()))
        .check(move |ctx, s| {
            let (lo, hi) = offenders(ctx, s, target);
            let exact = lo == hi || careless;
            match polarity {
                Polarity::Pplus | Polarity::Pminus => Observation::Set(if exact {
                    Answer::Exact(lo)
                } else {
                    Answer::Bounds { lo, hi }
                }),
                Polarity::Pn => {
                    // Bounds are trusted as given, so an honest check leaves the upper bound open when an
                    // opaque cone may hide further calls.
                    let h = if ctx.poison().is_empty() {
                        hi.len() as u64
                    } else {
                        u64::MAX
                    };
                    let l = lo.len() as u64;
                    Observation::Count(if exact {
                        Answer::Exact(l)
                    } else {
                        Answer::Bounds { lo: l, hi: h }
                    })
                }
                Polarity::P0 => Observation::Pair(
                    if exact {
                        Answer::Exact(lo.len().to_string())
                    } else {
                        Answer::Bounds {
                            lo: lo.len().to_string(),
                            hi: hi.len().to_string(),
                        }
                    },
                    Answer::Exact("1".into()),
                ),
                Polarity::Pc => {
                    // A reach observation is trusted as given, so an honest check folds any
                    // poison (certainty lost in an opaque cone) into its upper bound.
                    let poisoned = !ctx.poison().is_empty();
                    let t = if !lo.is_empty() {
                        Truth::Yes
                    } else if !hi.is_empty() || poisoned {
                        Truth::Unknown
                    } else {
                        Truth::No
                    };
                    let frontier = ctx.poison().into_iter().map(|p| p.node).collect();
                    Observation::reach(t, frontier)
                }
            }
        });
    if polarity == Polarity::Pn {
        p = p.threshold(threshold.0, threshold.1);
    }
    p
}

/// One completion of a subject: whether its own call resolves to the target, and how many calls
/// to the target the opaque cone adds.
#[derive(Debug, Clone, Copy)]
struct Completion {
    call_present: bool,
    count: u64,
}

fn completions(s: Spec) -> Vec<Completion> {
    let mut out = Vec::new();
    for shadowed in [false, true] {
        for hidden in [false, true] {
            if !s.dynamic && (shadowed || hidden) {
                continue;
            }
            let call_present = s.calls && !shadowed;
            out.push(Completion {
                call_present,
                count: u64::from(call_present) + u64::from(hidden),
            });
        }
    }
    out
}

/// Whether the polarity's rule fires in `c`, which is what a `Violation` must hold in.
fn fires(polarity: Polarity, c: Completion, threshold: (u64, ThresholdKind)) -> bool {
    match polarity {
        Polarity::Pplus | Polarity::Pc => c.count > 0,
        Polarity::Pminus => c.count == 0,
        Polarity::P0 => c.count != 1,
        Polarity::Pn => match threshold.1 {
            ThresholdKind::Max => c.count > threshold.0,
            ThresholdKind::Min => c.count < threshold.0,
        },
    }
}

fn spec_strategy() -> impl Strategy<Value = Spec> {
    (any::<bool>(), any::<bool>()).prop_map(|(calls, dynamic)| Spec { calls, dynamic })
}

fn polarity_strategy() -> impl Strategy<Value = Polarity> {
    prop_oneof![
        Just(Polarity::Pplus),
        Just(Polarity::Pminus),
        Just(Polarity::P0),
        Just(Polarity::Pn),
        Just(Polarity::Pc),
    ]
}

fn threshold_strategy() -> impl Strategy<Value = (u64, ThresholdKind)> {
    (
        0..3u64,
        prop_oneof![Just(ThresholdKind::Max), Just(ThresholdKind::Min)],
    )
}

fn verify(
    specs: &[Spec],
    polarity: Polarity,
    careless: bool,
    threshold: (u64, ThresholdKind),
) -> Result<(), TestCaseError> {
    let built = build(specs);
    let p = program(&built, polarity, careless, threshold);
    let out = p
        .evaluate(&built.model, &EvalConfig::default())
        .expect("a well-formed program evaluates");
    let mut violation_sites = 0usize;
    for r in &out.results {
        let i = built
            .subjects
            .iter()
            .position(|(u, _)| *u == r.subject)
            .expect("a result names a subject");
        let call = built.subjects[i].1;
        let comps = completions(specs[i]);
        for v in &r.verdicts {
            match v {
                Verdict::Violation { sites } => {
                    violation_sites += sites.len();
                    for site in sites {
                        if polarity == Polarity::Pplus {
                            // The site is the offending call, which must be one in every completion.
                            prop_assert_eq!(Some(*site), call, "site is not the call: {:?}", specs);
                            prop_assert!(
                                comps.iter().all(|c| c.call_present),
                                "finding at a call some completion shadows: {specs:?}"
                            );
                        } else {
                            prop_assert_eq!(*site, r.subject);
                        }
                    }
                    prop_assert!(
                        comps.iter().all(|c| fires(polarity, *c, threshold)),
                        "{polarity:?} fired but a completion disagrees: {specs:?} careless={careless}"
                    );
                }
                Verdict::Clean => prop_assert!(
                    comps.iter().all(|c| !fires(polarity, *c, threshold)),
                    "{polarity:?} certified clean but a completion fires: {specs:?} careless={careless}"
                ),
                Verdict::Unresolved { .. } | Verdict::NotApplicable => {}
            }
        }
        if !specs[i].dynamic {
            prop_assert!(
                r.examined
                    && !r
                        .verdicts
                        .iter()
                        .any(|v| matches!(v, Verdict::Unresolved { .. })),
                "a structure with no opaque cone was unresolved: {:?}",
                specs[i]
            );
        }
    }
    // Every violation site is reported as exactly one finding above Unresolved.
    let reported = out
        .findings
        .iter()
        .filter(|f| f.severity > gob_rules::Severity::Unresolved)
        .count();
    prop_assert_eq!(reported, violation_sites);
    Ok(())
}

proptest! {
    #[test]
    // frob:tests crates/gob-ir/src/eval/program.rs::RuleProgram
    fn every_finding_and_certified_clean_holds_in_every_completion(
        specs in prop::collection::vec(spec_strategy(), 1..=MAX_SUBJECTS),
        polarity in polarity_strategy(),
        careless in any::<bool>(),
        threshold in threshold_strategy(),
    ) {
        verify(&specs, polarity, careless, threshold)?;
    }
}

#[test]
// frob:tests crates/gob-ir/src/eval/program.rs::RuleProgram
fn a_careless_exact_answer_through_an_opaque_cone_is_never_certified() {
    // The call may be shadowed by the cone: claiming Exact(lo) for P- must not certify or fire.
    let specs = [Spec {
        calls: true,
        dynamic: true,
    }];
    for polarity in [
        Polarity::Pplus,
        Polarity::Pminus,
        Polarity::Pn,
        Polarity::P0,
    ] {
        verify(&specs, polarity, true, (0, ThresholdKind::Max)).expect("sound");
    }
}
