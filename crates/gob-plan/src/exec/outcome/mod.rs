//! From value to outcome: polarity, `unresolved when`, one finding per binding, witnesses
//! (grl-spec.md 7.0.5, 7.1 and 7.2).
//!
//! [`outcomes`] runs a plan and maps the Kleene value `F` of each binding to fire, Unresolved or
//! clean with no author code:
//!
//! | polarity | F = Yes | F = Unknown | F = No |
//! |---|---|---|---|
//! | P+, P0, Pn, Pc | fire | Unresolved | clean |
//! | P- | clean | Unresolved | fire |
//!
//! For P+ `F` is the binding's clauses and the `or` of the `report ... when` guards; for P- it is
//! the good-thing formula (the clauses after the plan's subject split), and a subject that is a
//! member only at status May cannot fire. A binding yields at most one [`Finding`]. The first
//! report whose guard is Yes produces it and earlier reports whose guard is Unknown become
//! notes. `unresolved when C` turns a fire or an Unresolved into Unresolved with its reason when
//! `C` is Yes or Unknown. Hits on unread (opaque or hole) nodes are Unresolved with reason
//! `parse-error`.
//!
//! Clean bindings of a P+ plan are never enumerated (the core prunes them), so an `unresolved
//! when` condition cannot turn one of them into an Unresolved; for P- every subject is visible.
//! `NotApplicable` is decided per (rule, language) before evaluation and is not this layer's.

mod reason;

use gob_ir::{NodeId, Truth};

pub use reason::Reason;

use super::core::{Env, Row, Verdict, evaluator, rows_of};
use super::relations::Relations;
use super::{ExecError, Input};
use crate::plan::{Op, OpId, Plan, Polarity, Quant, StrId, VarId};

/// What a binding came to.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    /// The rule fires on this binding.
    Fire,
    /// The rule could not decide this binding.
    Unresolved,
}

/// The first witness of a `some` clause, by source order.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Witness {
    /// The variable the `some` binds.
    pub var: VarId,
    /// The first member whose body is Yes (for a fire) or Unknown (a "possible witness").
    pub node: NodeId,
}

/// One finding: exactly one per binding that fires or is Unresolved.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Finding {
    /// Fire or Unresolved.
    pub kind: Kind,
    /// Index into [`Outcomes::rows`] of the binding.
    pub row: usize,
    /// The node the primary span is taken from, when the report's subject is a node.
    pub subject: Option<NodeId>,
    /// The report that produces the message (index into the plan's reports).
    pub report: usize,
    /// Earlier reports whose guard was Unknown: "may also" notes (indexes into the reports).
    pub notes: Vec<usize>,
    /// Why the binding is Unresolved; empty for a fire.
    pub reasons: Vec<Reason>,
    /// The first witness of each `some` clause, in clause order.
    pub witnesses: Vec<Witness>,
}

/// The result of running a plan to outcomes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Outcomes {
    /// Fires and Unresolved bindings in enumeration order.
    pub findings: Vec<Finding>,
    /// The bindings the findings refer to.
    pub rows: Vec<Row>,
    /// Bindings that were decided clean and kept by the core (P- subjects).
    pub clean: usize,
    /// Whether the evaluation budget ran out; unreached bindings are not in `rows`.
    pub truncated: bool,
}

/// Runs `plan` over `input` and maps every binding to its outcome.
///
/// # Errors
/// As [`super::run_with`].
pub fn outcomes(plan: &Plan, input: &Input<'_>, rels: &Relations) -> Result<Outcomes, ExecError> {
    let ev = evaluator(plan, input, rels)?;
    let run = rows_of(&ev);
    let p = plan.parts();
    let mut findings = Vec::new();
    let mut clean = 0;
    for (i, row) in run.rows.iter().enumerate() {
        let mut env = row.vars.clone();
        let (guards, w) = report_guards(&ev, &mut env);
        let (kind, mut reasons, report) = decide(p.polarity, row, &w, &guards, p);
        let mut kind = kind;
        // `unresolved when`: a Yes or Unknown condition replaces fire or clean.
        for u in &p.unresolved {
            let c = ev.eval(u.when, &mut env);
            if c.truth != Truth::No {
                kind = Some(Kind::Unresolved);
                reasons.push(Reason::When(p.strings[u.reason as usize].clone()));
            }
        }
        let Some(mut kind) = kind else {
            if p.polarity == Polarity::Pminus {
                clean += 1;
            }
            continue;
        };
        let subject = row.node(p.reports[report].subject);
        if kind == Kind::Fire && subject.is_some_and(|n| reason::touches_unread(ev.rd.model, n)) {
            kind = Kind::Unresolved;
            reasons.push(Reason::ParseError);
        }
        if kind == Kind::Unresolved && reasons.is_empty() {
            reasons.push(Reason::Hidden);
        }
        let notes = (0..report)
            .filter(|&r| guards[r].truth == Truth::Unknown)
            .collect();
        let witnesses = witnesses(&ev, &mut env, kind);
        findings.push(Finding {
            kind,
            row: i,
            subject,
            report,
            notes,
            reasons: if kind == Kind::Fire {
                Vec::new()
            } else {
                reasons
            },
            witnesses,
        });
    }
    tracing::debug!(
        rule = %p.rule, findings = findings.len(), clean, truncated = run.truncated, "outcomes"
    );
    Ok(Outcomes {
        findings,
        rows: run.rows,
        clean,
        truncated: run.truncated,
    })
}

/// Each report's guard under `env`, and their `or` (`Yes` when a report has no guard).
fn report_guards(ev: &super::core::Eval<'_>, env: &mut Env) -> (Vec<Verdict>, Verdict) {
    let mut w = Verdict::no();
    let guards: Vec<Verdict> = ev
        .plan
        .reports
        .iter()
        .map(|r| r.when.map_or_else(Verdict::yes, |c| ev.eval(c, env)))
        .collect();
    for g in &guards {
        w = w.or(g.clone());
    }
    (guards, w)
}

/// The polarity map: the outcome (`None` is clean), the reasons of an Unresolved and the
/// producing report.
fn decide(
    pol: Polarity,
    row: &Row,
    w: &Verdict,
    guards: &[Verdict],
    p: &crate::plan::PlanParts,
) -> (Option<Kind>, Vec<Reason>, usize) {
    let reasons = |v: &Verdict| {
        v.doubts
            .iter()
            .cloned()
            .map(Reason::Doubt)
            .collect::<Vec<_>>()
    };
    if pol == Polarity::Pminus {
        // F is the good-thing formula; the subject must be a certain member to fire.
        return match (row.formula.truth, row.verdict.truth) {
            (Truth::Yes, _) => (None, Vec::new(), 0),
            (Truth::No, Truth::Yes) => (Some(Kind::Fire), Vec::new(), 0),
            (Truth::No, _) => (Some(Kind::Unresolved), reasons(&row.verdict), 0),
            (Truth::Unknown, _) => {
                let mut r = reasons(&row.formula);
                r.extend(reasons(&row.verdict));
                (Some(Kind::Unresolved), r, 0)
            }
        };
    }
    let f = row.verdict.clone().and(w.clone());
    match f.truth {
        Truth::No => (None, Vec::new(), 0),
        Truth::Yes => {
            // A firing binding has a report whose guard is Yes, because F = Yes implies W = Yes.
            let report = guards
                .iter()
                .position(|g| g.truth == Truth::Yes)
                .unwrap_or(p.reports.len() - 1);
            (Some(Kind::Fire), Vec::new(), report)
        }
        Truth::Unknown => {
            let report = guards
                .iter()
                .position(|g| g.truth != Truth::No)
                .unwrap_or(0);
            (Some(Kind::Unresolved), reasons(&f), report)
        }
    }
}

/// The first witness (location order) of each top-level `some` clause: the first member whose
/// body is Yes for a fire, Unknown for an Unresolved.
fn witnesses(ev: &super::core::Eval<'_>, env: &mut Env, kind: Kind) -> Vec<Witness> {
    let want = if kind == Kind::Fire {
        Truth::Yes
    } else {
        Truth::Unknown
    };
    let quants: Vec<(VarId, StrId, OpId)> = ev
        .plan
        .clauses
        .iter()
        .filter_map(|&c| match ev.plan.ops[c as usize] {
            Op::Quant {
                quant: Quant::Some,
                var,
                kind,
                cond,
            } => Some((var, kind, cond)),
            _ => None,
        })
        .collect();
    quants
        .into_iter()
        .filter_map(|(var, k, cond)| {
            ev.witness(var, k, cond, want, env)
                .map(|node| Witness { var, node })
        })
        .collect()
}
