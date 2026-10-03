//! `PM001` and `PM002`: a milestone states its goal and exit criteria, and its epics are complete.
//!
//! The design table (`pm-enforcement.md` section 1) asks a milestone for a goal
//! statement, a target date or `unscheduled`, and at least one epic; an absent
//! target is the `unscheduled` bucket and is allowed. The pure cores
//! [`pm001`] and [`pm002`] take folded milestones (and ticket facts); [`evaluate`]
//! reads them from a ledger for `frob-check`. Descendants of a member epic are
//! found with the helpers `PM034` already exposes, not by a second walk.

use std::collections::{BTreeMap, BTreeSet};

use frob_ledger::{Ledger, TicketId};
use gob_rules::{Finding, Rule, RuleId, Severity};

use crate::error::Result;
use crate::model::Milestone;
use crate::rules::membership::{self, Claimant, handle, reached};

// frob:ticket 01M4069REJDB8FFVZFMJWAAVRY
/// A milestone has no goal statement or no exit criteria.
///
/// A release is planned against a goal and defined done by its exit criteria
/// (`milestone criterion add`). A blank goal, or a milestone with no criteria,
/// leaves "is it finished" unanswerable. A milestone with no target date is
/// `unscheduled`, which is allowed. Without milestone objects the rule is not
/// applicable.
///
/// ## Remedy
///
/// Give the milestone its goal and criteria, for example `frob milestone new
/// VERSION --goal "..." --criterion "..."` or `frob milestone criterion add
/// VERSION TEXT`.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM001",
    slug = "milestone-without-goal",
    family = "PM",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm001;

// frob:ticket 01M4069REJDB8FFVZFMJWAAVRY
/// A milestone has no epics, or a member epic is done while work under it is open.
///
/// A milestone's work arrives through its member epics (`milestone add EPIC
/// VERSION`). With none it plans nothing; and an epic that is already `done`
/// while a descendant ticket is still open claims a completeness it does not
/// have. Without milestone objects the rule is not applicable.
///
/// ## Remedy
///
/// Add an epic with `frob milestone add EPIC VERSION`, or reopen the epic (or
/// finish or move the open tickets under it).
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM002",
    slug = "milestone-epics-incomplete",
    family = "PM",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm002;

/// A ticket's state as `PM002` reads it: its fold facts plus whether it is `done`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Progress {
    /// The ticket facts shared with `PM034`.
    pub ticket: Claimant,
    /// True when the ticket's category is the terminal `done`.
    pub done: bool,
}

/// What [`evaluate`] found and how much it examined.
#[derive(Debug, Clone, Default)]
pub struct Evaluation {
    /// `PM001` and `PM002` findings.
    pub findings: Vec<Finding>,
    /// Milestones examined (each counts once per rule).
    pub subjects: usize,
}

fn rule_id<R: Rule>(rule: &R) -> RuleId {
    rule.meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

// frob:ticket 01M4069REJDB8FFVZFMJWAAVRY
/// Evaluate `PM001` over folded `milestones`: a blank goal or no exit criteria fires.
pub fn pm001(milestones: &[Milestone]) -> Vec<Finding> {
    let id = rule_id(&Pm001);
    let mut out = Vec::new();
    for m in milestones {
        let mut missing = Vec::new();
        if m.goal.trim().is_empty() {
            missing.push("a goal");
        }
        if m.criteria.is_empty() {
            missing.push("exit criteria");
        }
        if missing.is_empty() {
            continue;
        }
        tracing::debug!(version = %m.version, ?missing, "PM001: milestone incomplete");
        out.push(Finding::new(
            id.clone(),
            Severity::Warn,
            None,
            format!(
                "milestone {} has no {}; set the goal with `frob milestone new {} --goal \"...\"` and add criteria with `frob milestone criterion add {} \"...\"`",
                m.version,
                missing.join(" and no "),
                m.version,
                m.version
            ),
            &m.version,
        ));
    }
    out
}

// frob:ticket 01M4069REJDB8FFVZFMJWAAVRY
/// Evaluate `PM002` over folded `milestones` and ticket `progress`: no epics, or a done member epic with open descendants.
pub fn pm002(milestones: &[Milestone], progress: &[Progress]) -> Vec<Finding> {
    let id = rule_id(&Pm002);
    let tickets: Vec<Claimant> = progress.iter().map(|p| p.ticket.clone()).collect();
    let by_id: BTreeMap<TicketId, &Claimant> = tickets.iter().map(|t| (t.id, t)).collect();
    let done: BTreeSet<TicketId> = progress
        .iter()
        .filter(|p| p.done)
        .map(|p| p.ticket.id)
        .collect();
    let mut out = Vec::new();
    for m in milestones {
        if m.epics.is_empty() {
            tracing::debug!(version = %m.version, "PM002: milestone without epics");
            out.push(Finding::new(
                id.clone(),
                Severity::Warn,
                None,
                format!(
                    "milestone {} has no epics; run `frob milestone add <epic> {}`",
                    m.version, m.version
                ),
                &m.version,
            ));
            continue;
        }
        for epic in m.epics.iter().filter(|e| done.contains(e)) {
            let open: Vec<&Claimant> = tickets
                .iter()
                .filter(|t| t.id != *epic && !done.contains(&t.id))
                .filter(|t| reached(t, &by_id, &[*epic]))
                .collect();
            if open.is_empty() {
                continue;
            }
            tracing::debug!(epic = %epic, open = open.len(), "PM002: done epic with open descendants");
            let names = open
                .iter()
                .map(|t| format!("{} ({})", handle(t.id), t.title))
                .collect::<Vec<_>>()
                .join(", ");
            out.push(Finding::new(
                id.clone(),
                Severity::Warn,
                None,
                format!(
                    "epic {} of milestone {} is done but still has open work: {names}; reopen the epic or finish or move that work",
                    handle(*epic),
                    m.version
                ),
                &format!("{}>{epic}", m.version),
            ));
        }
    }
    out
}

/// Ticket facts with their done flag at the ledger tip.
fn progress(ledger: &Ledger) -> Result<Vec<Progress>> {
    let tickets = membership::claimants(ledger)?;
    let Some(tip) = ledger.tip_hex()? else {
        return Ok(Vec::new());
    };
    let mut out = Vec::with_capacity(tickets.len());
    for ticket in tickets {
        let done = ledger
            .read_ticket_at(&tip, ticket.id)?
            .is_some_and(|t| t.front.category.is_terminal());
        out.push(Progress { ticket, done });
    }
    Ok(out)
}

// frob:ticket 01M4069REJDB8FFVZFMJWAAVRY
/// Read milestones and tickets from `ledger` at its tip and run [`pm001`] and [`pm002`].
///
/// Returns an empty evaluation without milestones (the rules are then not applicable).
///
/// # Errors
///
/// Ledger read failures.
pub fn evaluate(ledger: &Ledger) -> Result<Evaluation> {
    let milestones = membership::milestones(ledger)?;
    if milestones.is_empty() {
        tracing::info!("PM001 and PM002 not applicable: no milestone objects");
        return Ok(Evaluation::default());
    }
    let mut findings = pm001(&milestones);
    findings.extend(pm002(&milestones, &progress(ledger)?));
    tracing::info!(
        milestones = milestones.len(),
        findings = findings.len(),
        "PM001 and PM002 evaluated"
    );
    Ok(Evaluation {
        findings,
        subjects: milestones.len(),
    })
}
