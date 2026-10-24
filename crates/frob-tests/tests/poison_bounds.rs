//! Pc and Pn bound evaluation must never fold poison into a passing verdict.
//!
//! A subject whose dependency cone holds an opaque region cannot be certified clean: an
//! `Exact` count taken through poison is downgraded, and a Pc closure that crosses a possible
//! edge stays Unresolved. Each case is paired with an unpoisoned control that does pass, so the
//! test fails both if poison is folded into a pass and if the controls stop being meaningful.

use gob_ir::{
    Answer, AttrValue, EvalConfig, Location, Model, NodeId, NodeSpec, Observation, Operator,
    Polarity, RuleOutcome, RuleProgram, TermBuilder, ThresholdKind, Verdict, reserved,
};
use gob_rules::{RuleId, Severity};
use gob_text::FileInterner;

/// A terse term builder handing out unit-width locations.
struct Build {
    tb: TermBuilder,
    file: gob_text::FileId,
    pos: u32,
}

impl Build {
    /// Start a term for `c.rs`.
    fn new() -> Self {
        let mut files = FileInterner::new();
        let file = files.intern("c.rs");
        Self {
            tb: TermBuilder::new("c.rs", "rust"),
            file,
            pos: 0,
        }
    }

    /// Add a node with the next location.
    fn node(&mut self, op: Operator, kids: &[NodeId]) -> NodeId {
        let loc = Location::text(self.file, self.pos, self.pos + 1);
        self.pos += 1;
        self.tb
            .node(NodeSpec::new(op, loc), kids)
            .expect("valid node")
    }

    /// Add a named function unit.
    fn function(&mut self, name: &str, kids: &[NodeId]) -> NodeId {
        let loc = Location::text(self.file, self.pos, self.pos + 1);
        self.pos += 1;
        let spec = NodeSpec::new(Operator::unit("function", "impl"), loc).named(name);
        self.tb.node(spec, kids).expect("valid node")
    }

    /// Add a call to `head`.
    fn call(&mut self, head: &str) -> NodeId {
        let h = self.node(Operator::reference(head), &[]);
        self.node(Operator::apply("call"), &[h])
    }

    /// Add an opaque region that may define any name.
    fn opaque(&mut self, defines: &str) -> NodeId {
        let loc = Location::text(self.file, self.pos, self.pos + 1);
        self.pos += 1;
        let spec = NodeSpec::new(Operator::opaque("dynamic:unresolvable", b"exec(code)"), loc)
            .attr(
                reserved::MAY_DEFINE,
                AttrValue::List(vec![AttrValue::Str(defines.into())]),
            );
        self.tb.node(spec, &[]).expect("valid node")
    }

    /// Finish into a lexical model rooted at a file unit over `kids`.
    fn model(mut self, kids: &[NodeId]) -> Model {
        let root = self.node(Operator::unit("file", "impl"), kids);
        Model::lexical(self.tb.finish(root).expect("valid term"))
    }
}

/// Parse a rule id fixture.
fn rule(id: &str) -> RuleId {
    id.parse().expect("valid rule id")
}

/// Every function unit of the model.
fn fn_units(ctx: &gob_ir::Ctx<'_>) -> Answer<Vec<NodeId>> {
    let t = ctx.term();
    Answer::Exact(
        t.units()
            .into_iter()
            .map(|u| u.node)
            .filter(|&n| t.node(n).name().is_some())
            .collect(),
    )
}

/// The verdicts of the function called `name`.
fn verdicts(out: &RuleOutcome, m: &Model, name: &str) -> Vec<Verdict> {
    let node = m
        .term()
        .units()
        .into_iter()
        .find(|u| u.symref.to_string() == format!("c.rs::{name}"))
        .expect("named unit")
        .node;
    out.results
        .iter()
        .find(|r| r.subject == node)
        .expect("subject result")
        .verdicts
        .clone()
}

/// Whether the subject `name` was examined (its answer known at least as bounds).
fn examined(out: &RuleOutcome, m: &Model, name: &str) -> bool {
    let node = m
        .term()
        .units()
        .into_iter()
        .find(|u| u.symref.to_string() == format!("c.rs::{name}"))
        .expect("named unit")
        .node;
    out.results
        .iter()
        .find(|r| r.subject == node)
        .expect("subject result")
        .examined
}

/// `calm` has two plain calls; `poisoned` has one plain call and an opaque region.
fn count_model() -> Model {
    let mut b = Build::new();
    let c1 = b.call("x");
    let c2 = b.call("y");
    let calm = b.function("calm", &[c1, c2]);
    let opaque = b.opaque("x");
    let c3 = b.call("z");
    let poisoned = b.function("poisoned", &[opaque, c3]);
    b.model(&[calm, poisoned])
}

/// A Pn program over `count_model` whose careless check reports `claimed` as an exact count
/// for every subject, after reading the cone (which records the poison).
fn pn_program(n: u64, kind: ThresholdKind, claimed: Answer<u64>) -> RuleProgram {
    RuleProgram::new(rule("COUNT001"), Polarity::Pn)
        .message("too many calls")
        .threshold(n, kind)
        .subjects(fn_units)
        .check(move |ctx, s| {
            let _ = ctx.descendants(s);
            Observation::Count(claimed.clone())
        })
}

/// Evaluate `p` over `m`.
fn run(m: &Model, p: &RuleProgram) -> RuleOutcome {
    p.evaluate(m, &EvalConfig::default()).expect("evaluates")
}

/// No finding of the outcome may be a pass-masquerading error-free certificate for `name`.
fn assert_not_certified(out: &RuleOutcome, m: &Model, name: &str) {
    let vs = verdicts(out, m, name);
    assert!(
        !vs.contains(&Verdict::Clean),
        "{name} was certified clean through poison: {vs:?}"
    );
    assert!(
        vs.iter().all(|v| matches!(v, Verdict::Unresolved { .. })),
        "{name} must be Unresolved, got {vs:?}"
    );
}

// frob:ticket 01M4P3HCGW50BCT6YD0T7M99CH
// frob:tests crates/gob-ir/src/eval/program.rs::RuleProgram.evaluate
#[test]
fn pc_and_pn_bounds_never_fold_poison_into_a_pass() {
    let m = count_model();

    // Pn, upper bound: an exact count under the threshold would pass if poison were folded.
    let max = pn_program(10, ThresholdKind::Max, Answer::Exact(3));
    let out = run(&m, &max);
    assert_eq!(verdicts(&out, &m, "calm"), [Verdict::Clean], "control");
    assert_not_certified(&out, &m, "poisoned");
    assert!(!examined(&out, &m, "poisoned"));
    assert!(
        out.findings
            .iter()
            .all(|f| f.severity == Severity::Unresolved)
    );
    assert_ne!(out.truth(), gob_ir::Truth::Yes);

    // Pn, lower bound: an exact count at or above the minimum would pass.
    let min = pn_program(3, ThresholdKind::Min, Answer::Exact(5));
    let out = run(&m, &min);
    assert_eq!(verdicts(&out, &m, "calm"), [Verdict::Clean], "control");
    assert_not_certified(&out, &m, "poisoned");

    // Pn, a poisoned exact count over the limit is not a certain violation either: poison
    // must not be folded into a failing result, so no Error finding may name it.
    let over = pn_program(10, ThresholdKind::Max, Answer::Exact(11));
    let out = run(&m, &over);
    assert!(matches!(
        &verdicts(&out, &m, "calm")[..],
        [Verdict::Violation { .. }]
    ));
    assert_not_certified(&out, &m, "poisoned");

    // Pn, bounds that straddle the threshold stay Unresolved, with or without poison.
    let straddle = pn_program(10, ThresholdKind::Max, Answer::Bounds { lo: 2, hi: 11 });
    let out = run(&m, &straddle);
    assert_not_certified(&out, &m, "calm");
    assert_not_certified(&out, &m, "poisoned");

    // Pn, an Unknown answer is never examined and never clean.
    let unknown = pn_program(10, ThresholdKind::Max, Answer::Unknown);
    let out = run(&m, &unknown);
    assert_not_certified(&out, &m, "poisoned");
    assert!(!examined(&out, &m, "poisoned"));

    // Pc: `d` calls `c` through an opaque region that may define `c`, and `c` calls `d`, so a
    // cycle is possible but not certain; `p` calls `q` and nothing calls back (control).
    let mut b = Build::new();
    let call_q = b.call("q");
    let fn_p = b.function("p", &[call_q]);
    let fn_q = b.function("q", &[]);
    let call_d = b.call("d");
    let fn_c = b.function("c", &[call_d]);
    let opaque = b.opaque("c");
    let call_c = b.call("c");
    let fn_d = b.function("d", &[opaque, call_c]);
    let m = b.model(&[fn_p, fn_q, fn_c, fn_d]);
    let cycle = RuleProgram::new(rule("CYCLE001"), Polarity::Pc)
        .message("call cycle")
        .subjects(fn_units)
        .check(|ctx, s| {
            let reach = ctx.rel_calls().closure();
            let frontier = ctx.poison().into_iter().map(|p| p.node).collect();
            Observation::reach(reach.get(s, s), frontier)
        });
    let out = run(&m, &cycle);
    assert_eq!(verdicts(&out, &m, "p"), [Verdict::Clean], "control");
    assert_eq!(verdicts(&out, &m, "q"), [Verdict::Clean], "control");
    for name in ["c", "d"] {
        assert_not_certified(&out, &m, name);
    }
    // The frontier names the poisoned nodes, so the maybe-set is never empty for them.
    let Verdict::Unresolved { maybe, .. } = &verdicts(&out, &m, "d")[0] else {
        panic!("d must be Unresolved");
    };
    assert!(!maybe.is_empty(), "poisoned frontier must be reported");
    assert!(
        out.findings
            .iter()
            .all(|f| f.severity == Severity::Unresolved)
    );
    assert_ne!(out.truth(), gob_ir::Truth::Yes);
}
