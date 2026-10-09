//! The executor core: bindings, conditions and three-valued connectives over a [`Model`].
//!
//! [`run`] takes a validated [`Plan`] and the model of one artifact and returns every binding
//! of the plan's `find` clauses whose clauses do not fail, in `(path, offset)` order, each with
//! the Kleene [`Verdict`] of its conditions (grl-spec.md 7.0 and 7.1). Outcomes (fire,
//! Unresolved, clean) are the polarity layer's job, not this one's.
//!
//! Edge verbs, `reaches`, side-relation finds and `count` read their data from
//! [`Relations`](super::relations::Relations); [`run`] supplies none, [`run_with`] supplies them.
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
pub(crate) use eval::Wired;
pub use field::{Datum, Scalar, compare};
pub use verdict::{Doubt, Verdict};

use eval::{Env, Eval, Matcher};
use kind::KindTest;

use crate::exec::relations::{Count, PEER_OF, Relations, SideRow};
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
    /// The plan names an edge relation or side table the caller did not supply.
    #[error("rule {rule}: no {what} `{name}` was supplied to the run")]
    MissingRelation {
        /// The rule.
        rule: String,
        /// `edge relation` or `side table`.
        what: &'static str,
        /// The relation's name as the plan writes it.
        name: String,
    },
    /// [`count`] was given an op that is not a quantifier.
    #[error("rule {rule}: op {op} is not a quantifier, so it cannot be counted")]
    NotCountable {
        /// The rule.
        rule: String,
        /// The op.
        op: OpId,
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
            .and_then(|v| match v {
                Val::Node(n) => Some(n),
                Val::Row(_) => None,
            })
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

/// Kind tests by kind word, compiled patterns by op and the supplied relations the plan names.
type Prepared<'r> = (HashMap<StrId, KindTest>, HashMap<OpId, Matcher>, Wired<'r>);

fn missing(p: &PlanParts, what: &'static str, name: &str) -> ExecError {
    ExecError::MissingRelation {
        rule: p.rule.clone(),
        what,
        name: name.to_owned(),
    }
}

/// Resolves every kind word, compiles every pattern and finds every relation the plan names,
/// or names what cannot run.
fn prepare<'r>(p: &PlanParts, rels: &'r Relations) -> Result<Prepared<'r>, ExecError> {
    let mut kinds = HashMap::new();
    let mut matchers = HashMap::new();
    let mut wired = Wired::default();
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
            Op::FindSide { table, .. } => {
                let name = &p.strings[*table as usize];
                let t = rels
                    .side
                    .get(name)
                    .ok_or_else(|| missing(p, "side table", name))?;
                wired.side.insert(*table, t);
            }
            Op::Verb { verb: word, .. } if p.strings[*word as usize] == PEER_OF => {}
            Op::Verb { verb: word, .. } | Op::Reaches { via: word, .. } => {
                let name = &p.strings[*word as usize];
                let r = rels
                    .edges
                    .get(name)
                    .ok_or_else(|| missing(p, "edge relation", name))?;
                wired.edges.insert(*word, r);
            }
            Op::And(_)
            | Op::Or(_)
            | Op::Not(_)
            | Op::Inside { .. }
            | Op::Order { .. }
            | Op::Cmp { .. } => {}
        }
    }
    Ok((kinds, matchers, wired))
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

/// Runs `plan` over `input` with no edge relations, side tables or knobs.
///
/// # Errors
/// As [`run_with`]; a plan that names a verb, `reaches` family or side table fails with
/// [`ExecError::MissingRelation`].
pub fn run(plan: &Plan, input: &Input<'_>) -> Result<Run, ExecError> {
    run_with(plan, input, &Relations::new())
}

/// Builds the evaluator for `plan`, or says why it cannot run.
fn evaluator<'a>(
    plan: &'a Plan,
    input: &Input<'a>,
    rels: &'a Relations,
) -> Result<Eval<'a>, ExecError> {
    let p = plan.parts();
    let (kinds, matchers, wired) = prepare(p, rels)?;
    Ok(Eval::new(
        p,
        input.model,
        input.source,
        kinds,
        matchers,
        wired,
    ))
}

/// Counts the members of the quantifier `quant` (an op of `plan`) under the bindings of `row`:
/// `[l, h]` where `l` counts those whose body is certainly true and `h` those for which it is not
/// certainly false, `h` unbounded when the model has unread regions (grl-spec.md 7.0.2).
///
/// # Errors
/// [`ExecError::NotCountable`] when `quant` is not a quantifier, plus the refusals of
/// [`run_with`].
pub fn count(
    plan: &Plan,
    input: &Input<'_>,
    rels: &Relations,
    quant: OpId,
    row: &Row,
) -> Result<Count, ExecError> {
    let p = plan.parts();
    let Some(&Op::Quant {
        var, kind, cond, ..
    }) = p.ops.get(quant as usize)
    else {
        return Err(ExecError::NotCountable {
            rule: p.rule.clone(),
            op: quant,
        });
    };
    let ev = evaluator(plan, input, rels)?;
    let mut env = row.vars.clone();
    Ok(ev.count(var, kind, cond, &mut env))
}

/// Runs `plan` over `input`, reading edges, side tables and knobs from `rels`.
///
/// # Errors
/// [`ExecError`] when the plan names a kind or op this executor cannot run, a pattern that
/// does not compile, or an edge relation or side table `rels` lacks; nothing is evaluated in
/// that case.
pub fn run_with(plan: &Plan, input: &Input<'_>, rels: &Relations) -> Result<Run, ExecError> {
    let p = plan.parts();
    let ev = evaluator(plan, input, rels)?;
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
    let (var, kind) = match ev.plan.ops[binder as usize] {
        Op::Find { var, kind } => (var, kind),
        Op::FindSide { var, table, .. } => {
            for index in 0..ev.side_rows(table) {
                env[usize::from(var)] = Some(Val::Row(SideRow { table, index }));
                let v = ready_verdict(ev, s, depth + 1, env, acc.clone());
                if v.truth != Truth::No {
                    enumerate(ev, s, depth + 1, env, v, rows);
                }
            }
            env[usize::from(var)] = None;
            return;
        }
        _ => unreachable!("binders are finds"),
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
