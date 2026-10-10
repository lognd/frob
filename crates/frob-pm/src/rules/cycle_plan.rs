//! `PM010`, `PM011` and `PM012`: an open or planned cycle is over capacity, has no goal, or holds work that is not ready.
//!
//! The pure cores ([`pm010`], [`pm011`], [`pm012`]) take folded facts;
//! [`evaluate`] reads cycles, delivery history and member tickets from a
//! ledger for `frob-check`. Capacity and the definition of ready come from
//! the same functions the verbs use ([`capacity`], [`ready_failures`]).

// frob:ticket 01M4CT036SCVJMN2E3GHDTYDAJ

use frob_ledger::Ledger;
use frob_ledger::model::{Category, Frontmatter, TicketType};
use gob_rules::{Finding, Rule, RuleId, Severity};

use crate::config::{PmTable, ReadyRequirement};
use crate::cycle::history::{deliveries, done_points};
use crate::cycle::velocity::{Capacity, capacity, committed};
use crate::error::Result;
use crate::model::{Cycle, State};
use crate::rules::cycle::cycles;
use crate::rules::membership::{Evaluation, handle};
use crate::store::PmStore;

/// An open or planned cycle commits more points than its capacity.
///
/// Advisory only. Capacity is the cycle's own `capacity_points`, else
/// `rolling_mean - k * stddev` once `[pm] min_history` cycles have closed;
/// before that nothing is enforced and the rule is silent.
///
/// ## Remedy
///
/// Move tickets out with `frob cycle unassign TICKET`, raise the cycle's
/// capacity, or accept the over-commit (`frob cycle assign --over-commit
/// --reason TEXT` records why).
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM010",
    slug = "cycle-over-capacity",
    family = "PM",
    severity = Advisory,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm010;

/// An open or planned cycle states no goal.
///
/// A cycle without a goal cannot be judged at its review: the team has
/// nothing to say it achieved.
///
/// ## Remedy
///
/// Give the cycle a goal: close and recreate it with `frob cycle new --goal
/// TEXT`.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM011",
    slug = "cycle-without-goal",
    family = "PM",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm011;

/// A not-yet-started member of an open or planned cycle fails the definition of ready.
///
/// Advisory. The predicates are `[pm] ready_requires`; the finding names the
/// failed ones. Started and finished members are not judged.
///
/// ## Remedy
///
/// Complete the ticket (`frob ticket update TICKET` to add points, scope,
/// criteria or a parent), or move it out of the cycle with `frob cycle
/// unassign TICKET`.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM012",
    slug = "cycle-member-not-ready",
    family = "PM",
    severity = Advisory,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm012;

fn rule_id<R: Rule + Default>() -> RuleId {
    R::default()
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

/// The predicates of `required` that the ticket `front` fails, in declaration order.
pub fn ready_failures(front: &Frontmatter, required: &[ReadyRequirement]) -> Vec<ReadyRequirement> {
    let present = |t: &Option<String>| t.as_deref().is_some_and(|s| !s.trim().is_empty());
    required
        .iter()
        .copied()
        .filter(|r| {
            let ok = match r {
                ReadyRequirement::StoryOrObjectiveQualified => {
                    front.ty != TicketType::Story
                        || (present(&front.persona)
                            && present(&front.capability)
                            && present(&front.outcome_text))
                }
                ReadyRequirement::Criteria => !front.acceptance.is_empty(),
                ReadyRequirement::Points => front.points.is_some(),
                ReadyRequirement::Scope => !front.scope.is_empty(),
                ReadyRequirement::Parent => front.parent.is_some(),
            };
            !ok
        })
        .collect()
}

/// Evaluate `PM010` for `cycle` committing `points` against `cap`: fires only over an enforced limit.
pub fn pm010(cycle: &Cycle, points: u32, cap: &Capacity) -> Option<Finding> {
    let limit = cap.limit()?;
    if points <= limit {
        return None;
    }
    tracing::debug!(cycle = %cycle.alias(), points, limit, "PM010: cycle over capacity");
    Some(Finding::new(
        rule_id::<Pm010>(),
        Severity::Advisory,
        None,
        format!(
            "cycle {} commits {points} points, over its {}",
            cycle.alias(),
            cap.describe()
        ),
        &format!("cycle:{}", cycle.alias()),
    ))
}

/// Evaluate `PM011` for `cycle`: fires on a blank goal.
pub fn pm011(cycle: &Cycle) -> Option<Finding> {
    if !cycle.goal.trim().is_empty() {
        return None;
    }
    tracing::debug!(cycle = %cycle.alias(), "PM011: cycle without goal");
    Some(Finding::new(
        rule_id::<Pm011>(),
        Severity::Warn,
        None,
        format!(
            "cycle {} has no goal; recreate it with `frob cycle new --goal TEXT`",
            cycle.alias()
        ),
        &format!("cycle:{}", cycle.alias()),
    ))
}

/// Evaluate `PM012` for member `ticket` (handle `handle`) of `cycle` failing `failed`: fires when any predicate failed.
pub fn pm012(cycle: &Cycle, handle: &str, failed: &[ReadyRequirement]) -> Option<Finding> {
    if failed.is_empty() {
        return None;
    }
    let names: Vec<&str> = failed.iter().map(|r| r.as_str()).collect();
    tracing::debug!(cycle = %cycle.alias(), ticket = handle, ?names, "PM012: member not ready");
    Some(Finding::new(
        rule_id::<Pm012>(),
        Severity::Advisory,
        None,
        format!(
            "{handle} in cycle {} is not ready: fails {}",
            cycle.alias(),
            names.join(", ")
        ),
        &format!("ticket:{handle}"),
    ))
}

/// Read cycles and member tickets from `ledger` and run `PM010`-`PM012` under the `[pm]` knobs `pm`.
///
/// # Errors
///
/// Ledger read failures.
pub fn evaluate(ledger: &Ledger, pm: &PmTable) -> Result<Evaluation> {
    let store = PmStore::new(ledger);
    let all = cycles(ledger)?;
    let done = done_points(&deliveries(store, ledger, &all));
    let mut out = Evaluation::default();
    for c in all.iter().filter(|c| c.state != State::Closed) {
        out.subjects += 1;
        out.findings.extend(pm011(c));
        let mut members: Vec<(TicketType, u32)> = Vec::new();
        for id in &c.tickets {
            let Ok(view) = ledger.show(*id) else {
                tracing::warn!(ticket = %id, cycle = %c.alias(), "member ticket unreadable; skipped by PM010-PM012");
                continue;
            };
            members.push((view.summary.ty, u32::from(view.summary.points.unwrap_or(0))));
            if matches!(view.summary.category, Category::Triage | Category::Todo) {
                let failed = ready_failures(&view.ticket.front, &pm.ready_requires);
                out.findings.extend(pm012(c, &handle(*id), &failed));
            }
        }
        let cap = capacity(c, &all, &done, pm.min_history, pm.capacity_k);
        out.findings.extend(pm010(c, committed(&members), &cap));
    }
    tracing::info!(
        subjects = out.subjects,
        findings = out.findings.len(),
        "PM010-PM012 evaluated"
    );
    Ok(out)
}
