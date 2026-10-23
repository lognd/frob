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
//! `NotApplicable` is decided per (rule, language) before evaluation: [`outcomes_in`] takes the
//! language and the capabilities the rule needs and returns [`Applicability::NotApplicable`] with
//! no findings (7.0.7), never a clean or an Unresolved result.
//!
//! A `certainly` or `possibly` that turned an Unknown into a definite answer is an assumption
//! (7.0.4): a fire that is Unresolved when those collapses are read as identity is conditional,
//! carries an [`Assumption`] with the reason `assumed:certainly@span`, and is capped at Advisory.

mod assume;
mod reason;

use gob_ir::{NodeId, Truth};

pub use assume::Assumption;
pub use reason::Reason;

use super::core::{Env, Eval, Row, Verdict, evaluator, identity_evaluator, rows_of};
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
    /// The `certainly`/`possibly` assumptions a fire rests on; non-empty means conditional.
    pub assumptions: Vec<Assumption>,
}

impl Finding {
    /// Whether this fire rests on a `certainly`/`possibly` assumption and is capped at Advisory.
    #[must_use]
    pub fn is_conditional(&self) -> bool {
        self.kind == Kind::Fire && !self.assumptions.is_empty()
    }
}

/// Whether a rule applies to the language it ran on (grl-spec.md 7.0.7).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Applicability {
    /// The rule applies; its findings are in [`Outcomes::findings`].
    Applicable,
    /// The capability matrix marks `capability` not applicable for the language: no findings, no
    /// clean count and no Unresolved.
    NotApplicable {
        /// The needed capability whose matrix cell is not applicable.
        capability: gob_caps::Capability,
    },
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
    /// Whether the rule applied to the language; not applicable runs are empty.
    pub applicability: Applicability,
}

/// Runs `plan` for `lang`: `NotApplicable` when any capability in `needs` is not applicable there
/// (decided before evaluation), else as [`outcomes`].
///
/// # Errors
/// As [`super::run_with`].
pub fn outcomes_in(
    plan: &Plan,
    input: &Input<'_>,
    rels: &Relations,
    lang: gob_caps::Lang,
    needs: &[gob_caps::Capability],
) -> Result<Outcomes, ExecError> {
    let gap = needs
        .iter()
        .copied()
        .find(|&c| gob_caps::precision(lang, c) == gob_caps::Precision::NotApplicable);
    let Some(capability) = gap else {
        return outcomes(plan, input, rels);
    };
    tracing::debug!(rule = %plan.parts().rule, ?lang, ?capability, "not applicable");
    Ok(Outcomes {
        findings: Vec::new(),
        rows: Vec::new(),
        clean: 0,
        truncated: false,
        applicability: Applicability::NotApplicable { capability },
    })
}

/// Runs `plan` over `input` and maps every binding to its outcome.
///
/// # Errors
/// As [`super::run_with`].
pub fn outcomes(plan: &Plan, input: &Input<'_>, rels: &Relations) -> Result<Outcomes, ExecError> {
    let ev = evaluator(plan, input, rels)?;
    let run = rows_of(&ev);
    let p = plan.parts();
    let assumed = assume::certainties(p);
    // V0: the same plan with the collapses read as identity, run only when a collapse exists.
    let identity = if assumed.is_empty() {
        None
    } else {
        let ev0 = identity_evaluator(plan, input, rels)?;
        let run0 = rows_of(&ev0);
        Some((ev0, run0))
    };
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
        let assumptions = match &identity {
            Some((ev0, run0)) if kind == Kind::Fire => {
                conditional(ev0, &run0.rows, row, &assumed, ev.rd.model, subject, &ev)
            }
            _ => Vec::new(),
        };
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
            assumptions,
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
        applicability: Applicability::Applicable,
    })
}

/// The assumptions behind a fire on `row`: all of `assumed` when the same binding is not a fire
/// with the collapses read as identity, else none. A binding the identity run did not reach
/// (its budget ran out) is left unconditional.
fn conditional(
    ev0: &Eval<'_>,
    rows0: &[Row],
    row: &Row,
    assumed: &[crate::plan::Certainty],
    model: &gob_ir::Model,
    subject: Option<NodeId>,
    ev: &Eval<'_>,
) -> Vec<Assumption> {
    let Some(base_row) = rows0.iter().find(|r| r.vars == row.vars) else {
        tracing::debug!("identity run did not reach the binding; fire stays unconditional");
        return Vec::new();
    };
    let mut env = base_row.vars.clone();
    let (guards, w) = report_guards(ev0, &mut env);
    let (kind0, _, _) = decide(ev0.plan.polarity, base_row, &w, &guards, ev0.plan);
    if kind0 == Some(Kind::Fire) {
        return Vec::new();
    }
    let span = assume::span_of(ev, model, subject);
    tracing::debug!(%span, "fire rests on a certainty assumption");
    assumed
        .iter()
        .map(|&certainty| Assumption {
            certainty,
            span: span.clone(),
        })
        .collect()
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
