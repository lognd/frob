//! `rule why`: the per-clause trace of one rule at one source line (grl-spec.md 2 step 5, 7.2).
//!
//! The trace uses the same executor as `rule check`: it re-runs the rule with its `where`
//! conditions added back one at a time, so the first condition that removes a candidate is the
//! clause that failed, and the doubts a condition adds (May edges, hidden regions) are the atoms
//! the polarity turns into Unresolved.

// frob:ticket 01M3ZX7H8FPEAY1X1WVW1PNXXN

use gob_ir::{NodeId, Truth};

use crate::exec::outcome::{Kind, Reason, outcomes};
use crate::exec::relations::Relations;
use crate::exec::{Doubt, ExecError, Input, Row, run_with};
use crate::grl::ast::{ClauseKind, CondKind, Containment, RelKind, Rule};
use crate::lower::{LowerError, lower_rule};
use crate::plan::{Plan, Polarity, Provenance};

/// Why a trace could not be produced.
#[derive(Debug, thiserror::Error)]
pub enum WhyError {
    /// The rule does not lower to a plan.
    #[error(transparent)]
    Lower(#[from] LowerError),
    /// The executor refused the plan.
    #[error(transparent)]
    Exec(#[from] ExecError),
}

/// One `where` condition of the rule and what it did to one candidate.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, schemars::JsonSchema)]
pub struct Step {
    /// The clause as written.
    pub clause: String,
    /// `yes`, `no` or `unknown`: the candidate's value once this clause is applied.
    pub value: String,
    /// The reason the clause failed (`no` on a P+ rule); `None` otherwise.
    pub failed: Option<String>,
    /// The May edges and other doubts this clause added, with what polarity does with them.
    pub doubts: Vec<String>,
}

/// One node on the asked line that the rule's `find` matches.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, schemars::JsonSchema)]
pub struct Candidate {
    /// `line:col` of the node.
    pub at: String,
    /// The clauses in source order.
    pub steps: Vec<Step>,
    /// `fire`, `unresolved` or `clean`: exactly what `rule check` reports for this node.
    pub outcome: String,
}

/// The whole trace for one rule at one line.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, schemars::JsonSchema)]
pub struct Why {
    /// The rule id.
    pub rule: String,
    /// `P+`, `P-`, `P0`, `Pn` or `Pc`.
    pub polarity: String,
    /// The asked line.
    pub line: u32,
    /// The candidates found on that line.
    pub candidates: Vec<Candidate>,
}

impl Why {
    /// The lines the text view prints.
    pub fn lines(&self) -> Vec<String> {
        let mut out = vec![format!("{} polarity {}", self.rule, self.polarity)];
        if self.candidates.is_empty() {
            out.push(format!(
                "0 candidates on line {}: no node matches the find",
                self.line
            ));
        }
        for c in &self.candidates {
            out.push(format!(
                "{} candidate{} at {}",
                self.candidates.len(),
                plural(self.candidates.len()),
                c.at
            ));
            for s in &c.steps {
                let mut l = format!("{}    {}", s.clause, s.value);
                if let Some(f) = &s.failed {
                    l = format!("{}    failed: {f}", s.clause);
                }
                out.push(l);
                out.extend(s.doubts.iter().map(|d| format!("    {d}")));
            }
            out.push(format!("outcome: {}", c.outcome));
        }
        out
    }
}

fn plural(n: usize) -> &'static str {
    if n == 1 { "" } else { "s" }
}

/// A removable condition: a top-level `where` clause or the `where` filter of a `find`.
#[derive(Clone, Copy)]
enum Unit {
    Where(usize),
    Filter(usize),
}

fn units(rule: &Rule) -> Vec<Unit> {
    rule.clauses
        .iter()
        .enumerate()
        .filter_map(|(i, c)| match &c.node {
            ClauseKind::Where(_) => Some(Unit::Where(i)),
            ClauseKind::Find(b) if b.filter.is_some() => Some(Unit::Filter(i)),
            _ => None,
        })
        .collect()
}

/// `rule` with only its first `keep` conditions.
fn prefix(rule: &Rule, all: &[Unit], keep: usize) -> Rule {
    let mut r = rule.clone();
    for u in all.iter().skip(keep) {
        if let Unit::Filter(i) = *u
            && let ClauseKind::Find(b) = &mut r.clauses[i].node
        {
            b.filter = None;
        }
    }
    let dropped: Vec<usize> = all
        .iter()
        .skip(keep)
        .filter_map(|u| {
            if let Unit::Where(i) = u {
                Some(*i)
            } else {
                None
            }
        })
        .collect();
    let mut i = 0;
    r.clauses.retain(|_| {
        i += 1;
        !dropped.contains(&(i - 1))
    });
    r
}

fn slice(text: &str, span: gob_text::Span) -> &str {
    let (s, e) = (
        u32::from(span.range.start()) as usize,
        u32::from(span.range.end()) as usize,
    );
    text.get(s..e).unwrap_or("").trim()
}

/// What the failed condition means at `at`, in words.
fn failure(cond: &crate::grl::ast::Cond, at: &str, text: &str) -> String {
    let inside = |c: &crate::grl::ast::Cond| match &c.node {
        CondKind::Rel { rel, .. } => match &rel.node {
            RelKind::Containment {
                dir: Containment::Inside,
                object,
                ..
            } => Some(slice(text, object.span()).to_owned()),
            _ => None,
        },
        _ => None,
    };
    if let CondKind::Not(inner) = &cond.node {
        if let Some(o) = inside(inner) {
            return format!("{at} is inside {o}");
        }
        return format!("`{}` holds at {at}", slice(text, inner.span));
    }
    match inside(cond) {
        Some(o) => format!("{at} is not inside {o}"),
        None => format!("`{}` does not hold at {at}", slice(text, cond.span)),
    }
}

fn subject_var(plan: &Plan) -> u16 {
    plan.parts().reports.first().map_or(0, |r| r.subject)
}

fn locate(input: &Input<'_>, n: NodeId) -> Option<(u32, u32)> {
    let span = input.model.term().node(n).location().span()?;
    let lc = input.source?.line_col(span.range.start())?;
    Some((lc.line, lc.col))
}

fn at_line(input: &Input<'_>, rows: &[Row], var: u16, line: u32) -> Vec<(NodeId, Row)> {
    rows.iter()
        .filter_map(|r| {
            let n = r.node(var)?;
            (locate(input, n)?.0 == line).then(|| (n, r.clone()))
        })
        .collect()
}

fn describe(d: &Doubt, input: &Input<'_>, pol: Polarity) -> String {
    let at = |n: NodeId| locate(input, n).map_or("?".to_owned(), |(l, c)| format!("{l}:{c}"));
    let what = Reason::Doubt(d.clone()).unresolved().code().to_owned();
    let effect = match pol {
        Polarity::Pminus => {
            "this makes the good thing Unknown, so the absence is Unresolved, not a fire"
        }
        _ => "Unknown keeps the rule Unresolved instead of a fire",
    };
    match d {
        Doubt::MayEdge { from, to } => {
            format!(
                "used a May edge {} -> {} ({what}); under polarity {}: {effect}",
                at(*from),
                at(*to),
                pol.symbol()
            )
        }
        other => format!(
            "doubt {what} ({other:?}); under polarity {}: {effect}",
            pol.symbol()
        ),
    }
}

/// Traces `rule` (whose text is `rule_text`) at `line` of `input`.
///
/// # Errors
/// [`WhyError`] when the rule does not lower or the executor refuses it.
pub fn why(
    rule: &Rule,
    rule_text: &str,
    input: &Input<'_>,
    rels: &Relations,
    line: u32,
) -> Result<Why, WhyError> {
    let full = lower_rule(rule, Provenance::Std)?;
    let pol = full.polarity();
    let all = units(rule);
    let mut runs = Vec::new();
    for k in 0..=all.len() {
        let plan = lower_rule(&prefix(rule, &all, k), Provenance::Std)?;
        let run = run_with(&plan, input, rels)?;
        runs.push(at_line(input, &run.rows, subject_var(&plan), line));
    }
    let out = outcomes(&full, input, rels)?;
    let mut nodes: Vec<NodeId> = runs[0].iter().map(|(n, _)| *n).collect();
    nodes.dedup();
    let candidates = nodes
        .into_iter()
        .map(|n| {
            let (l, c) = locate(input, n).unwrap_or((line, 0));
            let at = format!("{l}:{c}");
            let mut steps = Vec::new();
            let mut seen: Vec<Doubt> = Vec::new();
            let mut dead = false;
            for (k, u) in all.iter().enumerate() {
                let (text, cond) = match *u {
                    Unit::Where(i) => match &rule.clauses[i].node {
                        ClauseKind::Where(c) => {
                            (slice(rule_text, rule.clauses[i].span).to_owned(), c)
                        }
                        _ => continue,
                    },
                    Unit::Filter(i) => match &rule.clauses[i].node {
                        ClauseKind::Find(b) => match &b.filter {
                            Some(c) => (format!("where {}", slice(rule_text, c.span)), c),
                            None => continue,
                        },
                        _ => continue,
                    },
                };
                let row = runs[k + 1].iter().find(|(m, _)| *m == n).map(|(_, r)| r);
                let (truth, doubts) = match row {
                    Some(r) if pol == Polarity::Pminus => {
                        (r.formula.truth, r.formula.doubts.clone())
                    }
                    Some(r) => (r.verdict.truth, r.verdict.doubts.clone()),
                    None => (Truth::No, Vec::new()),
                };
                let new: Vec<String> = doubts
                    .iter()
                    .filter(|d| !seen.contains(d))
                    .map(|d| describe(d, input, pol))
                    .collect();
                seen = doubts;
                let value = match truth {
                    Truth::Yes => "yes",
                    Truth::No => "no",
                    Truth::Unknown => "unknown",
                };
                let failed = (truth == Truth::No && pol != Polarity::Pminus && !dead)
                    .then(|| failure(cond, &at, rule_text));
                dead |= failed.is_some();
                steps.push(Step {
                    clause: text,
                    value: value.to_owned(),
                    failed,
                    doubts: new,
                });
            }
            let outcome = match out.findings.iter().find(|f| f.subject == Some(n)) {
                Some(f) if f.kind == Kind::Fire => "fire",
                Some(_) => "unresolved",
                None => "clean",
            };
            Candidate {
                at,
                steps,
                outcome: outcome.to_owned(),
            }
        })
        .collect();
    Ok(Why {
        rule: rule.id.text.clone(),
        polarity: pol.symbol().to_owned(),
        line,
        candidates,
    })
}
