//! `PM034`: a ticket claims a milestone its epic ancestry does not reach.
//!
//! A milestone is a version whose members are epics (`milestone add EPIC
//! VERSION`); a ticket belongs to it only through an epic ancestor. During
//! bootstrap a ticket claims a milestone with the label `release:VERSION`.
//! The pure core [`pm034`] takes folded milestones and ticket facts;
//! [`evaluate`] reads them from a ledger for `frob-check`.

use std::collections::{BTreeMap, BTreeSet};

use frob_ledger::{Ledger, TicketId};
use gob_rules::{Finding, Rule, RuleId, Severity};

use crate::error::Result;
use crate::model::{Milestone, Object, ObjectKind};
use crate::store::PmStore;

/// Label prefix by which a ticket claims a milestone before membership lives on the milestone.
pub const CLAIM_PREFIX: &str = "release:";

// frob:ticket 01M4069RJJ4C73Z6GKKSV1E7PS
/// A ticket claims a milestone that its epic ancestry does not reach.
///
/// A ticket carrying `release:VERSION` must sit under (or be) one of the
/// epics that are members of milestone `VERSION`, and an epic that is a member
/// of a milestone must not have children claiming a different one. This is
/// the failure that scattered 72 tickets of one release with 70 of them
/// outside any epic. Without milestone objects the rule is not applicable.
///
/// ## Remedy
///
/// Add the ticket's epic to the milestone with `frob milestone add EPIC
/// VERSION`, reparent the ticket under a member epic with `frob ticket update
/// TICKET --parent EPIC`, or drop the `release:VERSION` label.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM034",
    slug = "milestone-member-outside-epics",
    family = "PM",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm034;

/// The facts of one ticket that `PM034` reads.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Claimant {
    /// The ticket.
    pub id: TicketId,
    /// Its title, for messages.
    pub title: String,
    /// Its parent, if any.
    pub parent: Option<TicketId>,
    /// Its labels.
    pub labels: Vec<String>,
}

/// What [`evaluate`] found and how much it examined.
#[derive(Debug, Clone, Default)]
pub struct Evaluation {
    /// `PM034` findings.
    pub findings: Vec<Finding>,
    /// Tickets claiming a known milestone plus member epics examined.
    pub subjects: usize,
}

/// `~` plus the last seven characters of `id`, the handle shown to humans.
fn handle(id: TicketId) -> String {
    format!("~{}", &id.random_part()[9..])
}

fn rule_id() -> RuleId {
    Pm034
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

/// Versions a ticket claims through `release:VERSION` labels, in label order.
fn claimed_versions(labels: &[String]) -> impl Iterator<Item = &str> {
    labels.iter().filter_map(|l| l.strip_prefix(CLAIM_PREFIX))
}

/// True when `start` or one of its ancestors is in `epics` (cycle-safe).
fn reached(start: &Claimant, by_id: &BTreeMap<TicketId, &Claimant>, epics: &[TicketId]) -> bool {
    let mut seen = BTreeSet::new();
    let mut at = Some(start.id);
    while let Some(id) = at {
        if epics.contains(&id) {
            return true;
        }
        if !seen.insert(id) {
            tracing::warn!(ticket = %id, "parent cycle while walking epic ancestry");
            return false;
        }
        at = by_id.get(&id).and_then(|t| t.parent);
    }
    false
}

fn names(epics: &[TicketId]) -> String {
    epics
        .iter()
        .map(|e| handle(*e))
        .collect::<Vec<_>>()
        .join(", ")
}

// frob:ticket 01M4069RJJ4C73Z6GKKSV1E7PS
/// Evaluate `PM034` over folded `milestones` and the ticket facts `tickets`.
///
/// A claim on a version without a milestone is ignored here (no epics to compare against).
pub fn pm034(milestones: &[Milestone], tickets: &[Claimant]) -> Evaluation {
    let by_id: BTreeMap<TicketId, &Claimant> = tickets.iter().map(|t| (t.id, t)).collect();
    let by_version: BTreeMap<&str, &Milestone> =
        milestones.iter().map(|m| (m.version.as_str(), m)).collect();
    let mut out = Evaluation::default();
    for t in tickets {
        for version in claimed_versions(&t.labels) {
            let Some(m) = by_version.get(version) else {
                tracing::debug!(ticket = %t.id, version, "claim on a version with no milestone");
                continue;
            };
            out.subjects += 1;
            if reached(t, &by_id, &m.epics) {
                continue;
            }
            tracing::debug!(ticket = %t.id, version, "PM034: claim outside the milestone's epics");
            let epics = if m.epics.is_empty() {
                "none yet".to_owned()
            } else {
                names(&m.epics)
            };
            out.findings.push(Finding::new(
                rule_id(),
                Severity::Warn,
                None,
                format!(
                    "ticket {} ({}) claims milestone {version} but no epic above it is a member of {version} (member epics: {epics}); run `frob milestone add <epic> {version}` or reparent the ticket under a member epic",
                    handle(t.id),
                    t.title
                ),
                &format!("{}@{version}", t.id),
            ));
        }
    }
    for m in milestones {
        for epic in &m.epics {
            out.subjects += 1;
            for child in tickets.iter().filter(|c| c.parent == Some(*epic)) {
                for other in claimed_versions(&child.labels).filter(|v| *v != m.version) {
                    tracing::debug!(epic = %epic, child = %child.id, other, "PM034: child claims another milestone");
                    out.findings.push(Finding::new(
                        rule_id(),
                        Severity::Warn,
                        None,
                        format!(
                            "epic {} is a member of milestone {} but its child {} ({}) claims milestone {other}; run `frob milestone add {} {other}` or reparent the child",
                            handle(*epic),
                            m.version,
                            handle(child.id),
                            child.title,
                            handle(*epic)
                        ),
                        &format!("{epic}>{}@{other}", child.id),
                    ));
                }
            }
        }
    }
    out
}

/// Folded milestones at the ledger tip.
///
/// # Errors
///
/// Ledger read failures.
pub fn milestones(ledger: &Ledger) -> Result<Vec<Milestone>> {
    Ok(PmStore::new(ledger)
        .list(ObjectKind::Milestone)?
        .into_iter()
        .filter_map(|o| match o {
            Object::Milestone(m) => Some(m),
            Object::Cycle(_) => None,
        })
        .collect())
}

// frob:ticket 01M4069WSTV5ZJMRPYR2YECX6Q
/// The facts of every ticket at the ledger tip, for `PM034` and the release readiness report.
///
/// # Errors
/// Ledger read failures.
pub fn claimants(ledger: &Ledger) -> Result<Vec<Claimant>> {
    let Some(tip) = ledger.tip_hex()? else {
        return Ok(Vec::new());
    };
    let mut tickets = Vec::new();
    for id in ledger.ticket_ids_at(&tip)? {
        if let Some(t) = ledger.read_ticket_at(&tip, id)? {
            tickets.push(Claimant {
                id,
                title: t.front.title,
                parent: t.front.parent,
                labels: t.front.labels,
            });
        }
    }
    Ok(tickets)
}

/// Read milestones and tickets from `ledger` at its tip and run [`pm034`].
///
/// Returns an empty evaluation without milestones (the rule is then not applicable).
///
/// # Errors
///
/// Ledger read failures.
pub fn evaluate(ledger: &Ledger) -> Result<Evaluation> {
    let milestones = milestones(ledger)?;
    if milestones.is_empty() {
        tracing::info!("PM034 not applicable: no milestone objects");
        return Ok(Evaluation::default());
    }
    let tickets = claimants(ledger)?;
    let out = pm034(&milestones, &tickets);
    tracing::info!(
        milestones = milestones.len(),
        findings = out.findings.len(),
        "PM034 evaluated"
    );
    Ok(out)
}
