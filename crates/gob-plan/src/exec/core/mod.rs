//! The executor core: bindings, conditions and three-valued connectives over a [`Model`].
//!
//! [`run`] takes a validated [`Plan`] and the model of one artifact and returns every binding
//! of the plan's `find` clauses whose clauses do not fail, in `(path, offset)` order, each with
//! the Kleene [`Verdict`] of its conditions (grl-spec.md 7.0 and 7.1). Outcomes (fire,
//! Unresolved, clean) are the polarity layer's job, not this one's.
//!
//! # Semantics implemented here
//!
//! - Connectives are Kleene's, via [`gob_ir::Truth`]; a [`Verdict`] keeps the doubts that decide
//!   an Unknown.
//! - `some` and `no` range over the kind's domain, a spread attribute counting as a member at
//!   status May, and add an Unknown disjunct when the model has unread regions.
//! - `inside` is transitive and `directly inside` one level (term ancestry); `before` and `after`
//!   order whole nodes of one file; `adjoins` needs the file text.
//! - Field comparison is Kleene over [`Datum`]: unknown data never decides.

mod eval;
mod field;
mod kind;
mod verdict;

use std::collections::HashMap;

use gob_ir::{Model, NodeId, Truth};
use gob_text::SourceText;
use regex::RegexBuilder;

pub use eval::Val;
pub use field::{Datum, Scalar, compare};
pub use verdict::{Doubt, Verdict};

use eval::{Env, Eval, Matcher};
use kind::KindTest;

use crate::plan::{Op, OpId, Operand, Plan, PlanParts, StrId, VarId};

/// Compiled regexes are refused above this size, in bytes (security.md 2.5).
const REGEX_SIZE_LIMIT: usize = 1 << 20;

/// Why a plan cannot run on this executor; always the plan's or the caller's fault, never a
/// silently empty answer.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[non_exhaustive]
pub enum ExecError {
    /// A kind word has no node test in this executor.
    #[error("rule {rule}: kind `{kind}` is not supported by the executor")]
    UnsupportedKind {
        /// The rule.
        rule: String,
        /// The kind word.
        kind: String,
    },
    /// An op is not supported by this executor.
    #[error("rule {rule}: op {op} (`{what}`) is not supported by the executor")]
    UnsupportedOp {
        /// The rule.
        rule: String,
        /// The op.
        op: OpId,
        /// Its name.
        what: &'static str,
    },
    /// A regex or glob pattern does not compile (or is too large).
    #[error("rule {rule}: pattern `{pattern}` is invalid: {why}")]
    BadPattern {
        /// The rule.
        rule: String,
        /// The pattern as written.
        pattern: String,
        /// Why.
        why: String,
    },
}

/// What a run reads: one artifact's model and, optionally, its text.
#[derive(Clone, Copy)]
pub struct Input<'a> {
    /// The artifact's model.
    pub model: &'a Model,
    /// The artifact's text; without it `.line`, `.text` of non-literals and `adjoins` are Unknown.
    pub source: Option<&'a SourceText>,
}

/// One binding of the `find` variables with the Kleene value of its conditions.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Row {
    /// The variable slots; quantifier variables are unbound again after evaluation.
    pub vars: Vec<Option<Val>>,
    /// The conjunction of memberships and condition clauses; never `No`.
    pub verdict: Verdict,
}

impl Row {
    /// The node bound to `var`, if any.
    pub fn node(&self, var: VarId) -> Option<NodeId> {
        self.vars
            .get(usize::from(var))
            .copied()
            .flatten()
            .map(|Val::Node(n)| n)
    }
}

/// The result of running a plan over one model.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Run {
    /// Surviving bindings in enumeration order (first `find` outermost, each in location order).
    pub rows: Vec<Row>,
    /// Whether the model has unread regions that may hide members of any kind.
    pub hidden: bool,
}

/// Op names for refusals.
fn op_name(op: &Op) -> &'static str {
    match op {
        Op::FindSide { .. } => "find side relation",
        Op::Verb { .. } => "verb",
        Op::Reaches { .. } => "reaches",
        _ => "op",
    }
}

/// Kind tests by kind word and compiled patterns by op.
type Prepared = (HashMap<StrId, KindTest>, HashMap<OpId, Matcher>);

/// Resolves every kind word and compiles every pattern, or names what cannot run.
fn prepare(p: &PlanParts) -> Result<Prepared, ExecError> {
    let mut kinds = HashMap::new();
    let mut matchers = HashMap::new();
    for (i, op) in p.ops.iter().enumerate() {
        let id = OpId::try_from(i).expect("validated plans have at most MAX_OPS ops");
        match op {
            Op::Find { kind, .. } | Op::Quant { kind, .. } => {
                let word = &p.strings[*kind as usize];
                let test = KindTest::from_word(word).ok_or_else(|| ExecError::UnsupportedKind {
                    rule: p.rule.clone(),
                    kind: word.clone(),
                })?;
                kinds.insert(*kind, test);
            }
            Op::MatchRegex { pattern, .. } => {
                let src = &p.strings[*pattern as usize];
                let re = RegexBuilder::new(src)
                    .size_limit(REGEX_SIZE_LIMIT)
                    .build()
                    .map_err(|e| bad_pattern(p, src, &e))?;
                matchers.insert(id, Matcher::Regex(re));
            }
            Op::MatchGlob { pattern, .. } => {
                let src = &p.strings[*pattern as usize];
                let g = globset::Glob::new(src).map_err(|e| bad_pattern(p, src, &e))?;
                matchers.insert(id, Matcher::Glob(g.compile_matcher()));
            }
            Op::FindSide { .. } | Op::Verb { .. } | Op::Reaches { .. } => {
                return Err(ExecError::UnsupportedOp {
                    rule: p.rule.clone(),
                    op: id,
                    what: op_name(op),
                });
            }
            Op::And(_)
            | Op::Or(_)
            | Op::Not(_)
            | Op::Inside { .. }
            | Op::Order { .. }
            | Op::Cmp { .. } => {}
        }
    }
    Ok((kinds, matchers))
}

fn bad_pattern(p: &PlanParts, src: &str, e: &dyn std::fmt::Display) -> ExecError {
    ExecError::BadPattern {
        rule: p.rule.clone(),
        pattern: src.to_owned(),
        why: e.to_string(),
    }
}

/// The free variables of the condition `id` (variables bound inside it are not free).
fn free_vars(p: &PlanParts, id: OpId, out: &mut Vec<VarId>) {
    let operand = |o: &Operand, out: &mut Vec<VarId>| {
        if let Operand::Var(v) | Operand::Field(v, _) = o {
            out.push(*v);
        }
    };
    match &p.ops[id as usize] {
        Op::And(cs) | Op::Or(cs) => cs.iter().for_each(|&c| free_vars(p, c, out)),
        Op::Not(c) => free_vars(p, *c, out),
        Op::Quant { var, cond, .. } => {
            let mut inner = Vec::new();
            free_vars(p, *cond, &mut inner);
            out.extend(inner.into_iter().filter(|v| v != var));
        }
        Op::Inside { sub: a, sup: b, .. } | Op::Order { a, b, .. } => out.extend([*a, *b]),
        Op::Verb {
            subject, object, ..
        } => out.extend([*subject, *object]),
        Op::Reaches { from, to, .. } => out.extend([*from, *to]),
        Op::Cmp { lhs, rhs, .. } => {
            operand(lhs, out);
            operand(rhs, out);
        }
        Op::MatchRegex { subject, .. } | Op::MatchGlob { subject, .. } => operand(subject, out),
        Op::Find { .. } | Op::FindSide { .. } => {}
    }
}

/// The clause schedule: binders in order, and for each depth the conditions that become
/// evaluable once that many binders are bound.
struct Schedule {
    binders: Vec<OpId>,
    ready: Vec<Vec<OpId>>,
}

fn schedule(p: &PlanParts) -> Schedule {
    let binders: Vec<OpId> = p
        .clauses
        .iter()
        .copied()
        .filter(|&c| matches!(p.ops[c as usize], Op::Find { .. } | Op::FindSide { .. }))
        .collect();
    let mut depth_of: HashMap<VarId, usize> = HashMap::new();
    for (i, &b) in binders.iter().enumerate() {
        if let Op::Find { var, .. } | Op::FindSide { var, .. } = p.ops[b as usize] {
            depth_of.insert(var, i + 1);
        }
    }
    let mut ready = vec![Vec::new(); binders.len() + 1];
    for &c in &p.clauses {
        if binders.contains(&c) {
            continue;
        }
        let mut vars = Vec::new();
        free_vars(p, c, &mut vars);
        let at = vars.iter().map(|v| depth_of[v]).max().unwrap_or(0);
        ready[at].push(c);
    }
    Schedule { binders, ready }
}

/// Runs `plan` over `input`.
///
/// # Errors
/// [`ExecError`] when the plan names a kind or op this executor cannot run, or a pattern that
/// does not compile; nothing is evaluated in that case.
pub fn run(plan: &Plan, input: &Input<'_>) -> Result<Run, ExecError> {
    let p = plan.parts();
    let (kinds, matchers) = prepare(p)?;
    let ev = Eval::new(p, input.model, input.source, kinds, matchers);
    let sched = schedule(p);
    let mut rows = Vec::new();
    let mut env: Env = vec![None; usize::from(p.vars)];
    let start = ready_verdict(&ev, &sched, 0, &mut env, Verdict::yes());
    if start.truth != Truth::No {
        enumerate(&ev, &sched, 0, &mut env, start, &mut rows);
    }
    tracing::debug!(rule = %p.rule, rows = rows.len(), hidden = ev.hidden, "plan run");
    Ok(Run {
        rows,
        hidden: ev.hidden,
    })
}

/// Conjoins `acc` with the conditions that become evaluable at `depth`.
fn ready_verdict(
    ev: &Eval<'_>,
    s: &Schedule,
    depth: usize,
    env: &mut Env,
    mut acc: Verdict,
) -> Verdict {
    for &c in &s.ready[depth] {
        acc = acc.and(ev.eval(c, env));
        if acc.truth == Truth::No {
            break;
        }
    }
    acc
}

fn enumerate(
    ev: &Eval<'_>,
    s: &Schedule,
    depth: usize,
    env: &mut Env,
    acc: Verdict,
    rows: &mut Vec<Row>,
) {
    let Some(&binder) = s.binders.get(depth) else {
        rows.push(Row {
            vars: env.clone(),
            verdict: acc,
        });
        return;
    };
    let Op::Find { var, kind } = ev.plan.ops[binder as usize] else {
        unreachable!("side-relation finds are refused before the run starts");
    };
    for &(n, member) in ev.domain(kind).iter() {
        env[usize::from(var)] = Some(Val::Node(n));
        let mut v = acc.clone();
        if member == Truth::Unknown {
            v = v.and(Verdict::unknown(Doubt::Member { node: n }));
        }
        let v = ready_verdict(ev, s, depth + 1, env, v);
        if v.truth != Truth::No {
            enumerate(ev, s, depth + 1, env, v, rows);
        }
    }
    env[usize::from(var)] = None;
}
