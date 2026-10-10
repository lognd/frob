//! `doctor`: ledger integrity (fold equals frontmatter, dangling links, event order).

use gob_rules::Finding;
use schemars::JsonSchema;
use serde::Serialize;

use crate::error::Result;
use crate::event::EventBody;
use crate::fold::fold;
use crate::id::TicketId;
use crate::ledger::Ledger;
use crate::rules::{tick001, tick001_unreadable, tick003};

/// Seconds an event's `at` may differ from its ULID time before it is flagged.
pub const CLOCK_SKEW_SECS: i64 = 600;

/// Seconds an event's ULID may be later than its `at` before it is flagged.
///
/// A command stamps every event with one clock reading taken when it starts, while each ULID is
/// minted when the event is built; long commands (`land`, evidence runs, transitions after a
/// test run) therefore legitimately lag `at` behind the ULID, up to the command's duration.
pub const MINT_LAG_SECS: i64 = 6 * 3600;

/// Why an event's `at` and ULID time disagree, or `None` when they are consistent.
///
/// An `at` later than the ULID by more than [`CLOCK_SKEW_SECS`] is impossible for an honest
/// writer; a ULID later than `at` is flagged only beyond [`MINT_LAG_SECS`].
// frob:ticket 01M4HQ2VER5JCH39RCHY8NVYNZ
pub fn order_skew(at_secs: i64, ulid_secs: i64) -> Option<i64> {
    let ahead = at_secs - ulid_secs;
    let lag = -ahead;
    if ahead > CLOCK_SKEW_SECS || lag > MINT_LAG_SECS {
        Some(ahead.abs())
    } else {
        None
    }
}

/// A problem that is not one of the TICK rules.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Issue {
    /// Stable code: `E-DOCTOR-UNREADABLE`, `E-DOCTOR-ORDER`, `E-DOCTOR-CONFLICT`, `E-DOCTOR-ID`.
    pub code: String,
    /// The ticket concerned.
    pub ticket: TicketId,
    /// What is wrong.
    pub message: String,
}

/// The result of [`Ledger::doctor`].
#[derive(Debug, Clone)]
pub struct DoctorReport {
    /// Tickets examined.
    pub tickets: usize,
    /// Events examined.
    pub events: usize,
    /// `TICK001` and `TICK003` findings.
    pub findings: Vec<Finding>,
    /// Other problems.
    pub issues: Vec<Issue>,
    /// Tickets whose frontmatter `--fix` rewrote.
    pub fixed: Vec<TicketId>,
}

impl DoctorReport {
    /// True when nothing is wrong.
    pub fn is_clean(&self) -> bool {
        self.findings.is_empty() && self.issues.is_empty()
    }
}

/// One ticket's card and events from the bulk walks; `None` where a bulk read failed.
struct Prefetched {
    card: Option<Result<Option<crate::model::Ticket>>>,
    events: Option<Vec<crate::event::Event>>,
}

impl Ledger {
    /// Re-fold every ticket from the ledger tip and compare with its frontmatter.
    ///
    /// With `fix`, tickets whose frontmatter differs from the fold are
    /// rewritten (one `reconcile` commit each).
    ///
    /// # Errors
    ///
    /// Git read or commit failures; unreadable tickets are reported as issues, not errors.
    pub fn doctor(&self, fix: bool) -> Result<DoctorReport> {
        let ref_name = self.ledger_ref()?;
        let mut report = DoctorReport {
            tickets: 0,
            events: 0,
            findings: Vec::new(),
            issues: Vec::new(),
            fixed: Vec::new(),
        };
        let Some(tip) = self.tip_of(&ref_name)? else {
            return Ok(report);
        };
        let hex = tip.to_string();
        let ids = self.ticket_ids_at(&hex)?;
        let known: std::collections::BTreeSet<TicketId> = ids.iter().copied().collect();
        let mut to_fix = Vec::new();
        if self.layout() == crate::layout::Layout::Branch {
            for id in &self.branch_scan_at(&hex)?.with_events {
                if !known.contains(id) {
                    report.issues.push(Issue {
                        code: "E-DOCTOR-ORPHAN-EVENTS".to_owned(),
                        ticket: *id,
                        message: format!("`.events/{id}/` has no ticket file naming that id"),
                    });
                }
            }
        }
        // One tree walk each for every card and every event; a failed bulk read falls back to
        // per-ticket reads, which report the unreadable ticket individually.
        let mut cards = self.read_tickets_many_at(&hex, &ids).ok();
        let mut event_sets = self.read_events_many_at(&hex, &known).ok();
        tracing::debug!(
            bulk_cards = cards.is_some(),
            bulk_events = event_sets.is_some(),
            "doctor prefetch"
        );
        for id in &ids {
            report.tickets += 1;
            let pre = Prefetched {
                card: cards.as_mut().and_then(|m| m.remove(id)),
                events: event_sets.as_mut().and_then(|m| m.remove(id)),
            };
            if self.check_ticket(&hex, *id, &known, pre, &mut report) {
                to_fix.push(*id);
            }
        }
        if fix {
            for id in to_fix {
                if self.reconcile(id)?.is_some() {
                    report.fixed.push(id);
                }
            }
            let fixed = &report.fixed;
            report.findings.retain(|f| {
                !(f.rule.as_str() == "TICK001"
                    && fixed.iter().any(|i| f.message.contains(&i.to_string())))
            });
        }
        tracing::info!(
            tickets = report.tickets,
            findings = report.findings.len(),
            issues = report.issues.len(),
            fixed = report.fixed.len(),
            "doctor finished"
        );
        Ok(report)
    }

    /// Check one ticket against its events; true when its frontmatter needs re-folding.
    fn check_ticket(
        &self,
        hex: &str,
        id: TicketId,
        known: &std::collections::BTreeSet<TicketId>,
        pre: Prefetched,
        report: &mut DoctorReport,
    ) -> bool {
        let issue = |code: &str, message: String| Issue {
            code: code.to_owned(),
            ticket: id,
            message,
        };
        let stored = match pre.card.unwrap_or_else(|| self.read_ticket_at(hex, id)) {
            Ok(Some(t)) => t,
            Ok(None) => return false,
            Err(e) => {
                // The events are the source of truth: a foldable ticket is repairable.
                let foldable = self
                    .read_events_at(hex, id)
                    .is_ok_and(|ev| fold(id, &ev).is_ok());
                if foldable {
                    report.findings.push(tick001_unreadable(id, &e.to_string()));
                } else {
                    report
                        .issues
                        .push(issue("E-DOCTOR-UNREADABLE", e.to_string()));
                }
                return foldable;
            }
        };
        if stored.front.id != id {
            report.issues.push(issue(
                "E-DOCTOR-ID",
                format!(
                    "directory {id} holds a ticket whose id is {}",
                    stored.front.id
                ),
            ));
        }
        let events = match pre.events.map_or_else(|| self.read_events_at(hex, id), Ok) {
            Ok(e) => e,
            Err(e) => {
                report
                    .issues
                    .push(issue("E-DOCTOR-UNREADABLE", e.to_string()));
                return false;
            }
        };
        report.events += events.len();
        for ev in &events {
            let ulid_secs = i64::try_from(ev.id.timestamp_ms() / 1000).unwrap_or(0);
            if let Some(skew) = order_skew(ev.at.unix(), ulid_secs) {
                report.issues.push(issue(
                    "E-DOCTOR-ORDER",
                    format!(
                        "event {} has at={} but its ULID says a time {skew}s away",
                        ev.id, ev.at
                    ),
                ));
            }
        }
        if let Some(first) = events.first()
            && !matches!(first.body, EventBody::Create(_))
        {
            report.issues.push(issue(
                "E-DOCTOR-ORDER",
                format!(
                    "event {} ({}) sorts before the create event",
                    first.id, first.kind
                ),
            ));
        }
        report
            .findings
            .extend(tick003(&stored.front, &|t| known.contains(&t)));
        match fold(id, &events) {
            Ok(folded) => {
                for c in &folded.conflicts {
                    report.issues.push(issue(
                        "E-DOCTOR-CONFLICT",
                        format!(
                            "event {} changed `{}` expecting {} but found {}",
                            c.event,
                            c.field,
                            c.expected.as_deref().unwrap_or("unset"),
                            c.found.as_deref().unwrap_or("unset")
                        ),
                    ));
                }
                if let Some(f) = tick001(id, &folded.ticket, &stored) {
                    report.findings.push(f);
                    return true;
                }
                false
            }
            Err(e) => {
                report
                    .issues
                    .push(issue("E-DOCTOR-UNREADABLE", e.to_string()));
                false
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob-ledger/src/doctor.rs::order_skew
    #[test]
    fn a_command_frozen_clock_lagging_the_ulid_is_not_flagged() {
        assert_eq!(order_skew(1_000, 1_000 + 1_875), None);
        assert_eq!(order_skew(1_000, 1_000 + MINT_LAG_SECS), None);
    }

    // frob:tests crates/frob-ledger/src/doctor.rs::order_skew
    #[test]
    fn an_at_ahead_of_its_ulid_or_a_huge_lag_is_flagged() {
        assert_eq!(order_skew(1_000 + 601, 1_000), Some(601));
        assert_eq!(order_skew(1_000 + 600, 1_000), None);
        assert_eq!(
            order_skew(1_000, 1_000 + MINT_LAG_SECS + 1),
            Some(MINT_LAG_SECS + 1)
        );
    }
}
