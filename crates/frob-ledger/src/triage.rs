//! The triage inbox: `ticket triage accept|decline|snooze|duplicate|list` (design: `tickets.md` sections 3 and 11).
//!
//! A decision is a `triage` event plus the events it implies: accept writes a
//! `transition` triage to todo, decline a `transition` to done with outcome
//! `wont-fix`, duplicate a `link` (`duplicates`) and a `transition` to done with
//! outcome `duplicate`, snooze nothing else. One call decides any number of
//! tickets and lands them in one ledger commit; a repeat of a decision that
//! already holds writes nothing. Tickets are refused, naming the remedy, when
//! they are not in the inbox and were not already given the same decision;
//! one refusal aborts the whole call before anything is written.
// frob:ticket 01M44C546DQRE4D11HHPM0HX6M

use std::collections::BTreeSet;

use gob_git::{CommitOptions, Oid, RelPath};
use schemars::JsonSchema;
use serde::Serialize;

use crate::error::{LedgerError, Result};
use crate::event::{Event, EventBody, LinkData, TransitionData, TriageData};
use crate::fold::fold;
use crate::id::TicketId;
use crate::index::{ListFilter, Summary};
use crate::ledger::Ledger;
use crate::links::{Edge, check_add};
use crate::model::{Category, LinkKind, LinkOp, Outcome, Stamp, TriageAction};

/// Refusal code for a ticket that is neither in triage nor already decided.
pub const NOT_IN_TRIAGE: &str = "E-TRIAGE-NOT-IN-TRIAGE";

/// One triage decision to apply to every ticket of a call.
#[derive(Debug, Clone)]
pub struct TriageRequest {
    /// What to decide.
    pub action: TriageAction,
    /// Snooze only: the instant the ticket returns to the inbox.
    pub until: Option<Stamp>,
    /// Why; required for decline, optional elsewhere.
    pub reason: Option<String>,
    /// Duplicate only: the ticket this one duplicates.
    pub target: Option<TicketId>,
}

/// What a call did to one ticket.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "kebab-case")]
pub enum TriageStatus {
    /// The decision was written.
    Applied,
    /// The ticket already carried this decision; nothing was written.
    Already,
}

/// The per-ticket line of a [`TriageReport`].
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TriageEntry {
    /// Full ULID.
    pub id: TicketId,
    /// Handle with `~`.
    pub handle: String,
    /// Title.
    pub title: String,
    /// Written or already held.
    pub status: TriageStatus,
    /// Category after the call.
    pub category: Category,
    /// Outcome after the call, when done.
    pub outcome: Option<Outcome>,
}

/// The result of one triage call: every ticket in the order given, and the single commit.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TriageReport {
    /// One entry per distinct ticket.
    pub entries: Vec<TriageEntry>,
    /// The ledger commit, absent when every ticket was already decided.
    pub commit: Option<String>,
    /// Notes the caller must surface (checkouts the commit could not sync).
    #[serde(skip)]
    pub warnings: Vec<String>,
}

/// A ticket of the inbox listing.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct InboxEntry {
    /// The ticket's index row.
    #[serde(flatten)]
    pub summary: Summary,
    /// Set when the ticket is snoozed (only listed with `all`): when it returns.
    pub snoozed_until: Option<Stamp>,
}

/// The latest `triage` event among `events` (fold order), if any.
fn latest_triage(events: &[Event]) -> Option<&TriageData> {
    events.iter().rev().find_map(|e| match &e.body {
        EventBody::Triage(d) => Some(d),
        _ => None,
    })
}

/// Whether the latest decision on a ticket is `req` again.
fn holds(latest: Option<&TriageData>, req: &TriageRequest) -> bool {
    latest.is_some_and(|d| d.action == req.action && d.until == req.until)
}

/// The refusal for a ticket outside the inbox.
fn not_in_triage(s: &Summary, req: &TriageRequest) -> LedgerError {
    LedgerError::GuardRefused {
        code: NOT_IN_TRIAGE.to_owned(),
        message: format!(
            "{} is {}{}, not in triage, so it cannot be {}d",
            s.handle,
            s.category,
            s.outcome.map_or(String::new(), |o| format!(" ({o})")),
            req.action
        ),
        remedy: Some("frob ticket list --category triage".to_owned()),
    }
}

impl Ledger {
    /// Apply `req` to every ticket of `ids` and commit the lot once; `now` is the clock for snooze checks.
    ///
    /// # Errors
    ///
    /// [`LedgerError::Invalid`] for a decline without a reason, a
    /// duplicate without a target, a snooze without a future `until`, or a
    /// duplicate of itself; [`LedgerError::GuardRefused`] (`E-TRIAGE-NOT-IN-TRIAGE`)
    /// for a ticket neither in triage nor already decided this way;
    /// [`LedgerError::LinkRejected`] when the duplicate link is refused;
    /// lookup and store failures. Nothing is written on any error.
    pub fn triage(
        &self,
        ids: &[TicketId],
        req: &TriageRequest,
        now: Stamp,
    ) -> Result<TriageReport> {
        self.require_dir_layout("ticket triage")?;
        validate(req, now)?;
        let s = self.synced()?;
        let hex = s.tip.map(|t| t.to_string());
        let actor = self.actor()?;
        let edges = if req.action == TriageAction::Duplicate {
            s.index.edges()?
        } else {
            Vec::new()
        };
        let mut seen = BTreeSet::new();
        let mut planned: Vec<(TicketId, Vec<Event>)> = Vec::new();
        let mut entries: Vec<TriageEntry> = Vec::new();
        for &id in ids {
            if !seen.insert(id) {
                continue;
            }
            let (summary, _) = Self::load(&s, id)?;
            let in_triage = summary.category == Category::Triage;
            let existing = match &hex {
                Some(h) => self.read_events_at(h, id)?,
                None => Vec::new(),
            };
            if holds(latest_triage(&existing), req) {
                tracing::debug!(ticket = %id, action = %req.action, "triage already held");
                entries.push(entry(&summary, TriageStatus::Already));
                continue;
            }
            if !in_triage {
                tracing::info!(ticket = %id, category = %summary.category, action = %req.action, "triage refused: not in triage");
                return Err(not_in_triage(&summary, req));
            }
            let mut events = Vec::new();
            if let (TriageAction::Duplicate, Some(target)) = (req.action, req.target) {
                if s.index.summary(target)?.is_none() {
                    return Err(LedgerError::NotFound {
                        input: target.to_string(),
                    });
                }
                if !edges.contains(&Edge::normalize(id, LinkKind::Duplicates, target)) {
                    let ty_of = |t: TicketId| s.index.summary(t).ok().flatten().map(|x| x.ty);
                    check_add(&edges, &ty_of, id, LinkKind::Duplicates, target)?;
                    events.push(Event::new(
                        self.now(),
                        &actor,
                        EventBody::Link(LinkData {
                            op: LinkOp::Add,
                            link: LinkKind::Duplicates,
                            target,
                        }),
                    ));
                }
            }
            if let Some((to, outcome)) = destination(req.action) {
                events.push(Event::new(
                    self.now(),
                    &actor,
                    EventBody::Transition(TransitionData {
                        from: Category::Triage,
                        to,
                        outcome,
                        reason: req.reason.clone(),
                    }),
                ));
            }
            events.push(Event::new(
                self.now(),
                &actor,
                EventBody::Triage(TriageData {
                    action: req.action,
                    until: req.until,
                    reason: req.reason.clone(),
                }),
            ));
            entries.push(TriageEntry {
                category: destination(req.action).map_or(Category::Triage, |d| d.0),
                outcome: destination(req.action).and_then(|d| d.1),
                ..entry(&summary, TriageStatus::Applied)
            });
            planned.push((id, events));
        }
        drop(s);
        let mut report = TriageReport {
            entries,
            commit: None,
            warnings: Vec::new(),
        };
        if planned.is_empty() {
            tracing::info!(action = %req.action, tickets = report.entries.len(), "triage: nothing to write");
            return Ok(report);
        }
        let (oid, warnings) = self.commit_triage(&planned, req, hex.as_deref())?;
        report.commit = Some(oid.to_string());
        report.warnings = warnings;
        Ok(report)
    }

    /// Write every planned ticket's events and re-folded frontmatter in one commit.
    fn commit_triage(
        &self,
        planned: &[(TicketId, Vec<Event>)],
        req: &TriageRequest,
        hex: Option<&str>,
    ) -> Result<(Oid, Vec<String>)> {
        let dir = &self.cfg.dir;
        let mut changes = Vec::new();
        let mut titles = Vec::new();
        for (id, events) in planned {
            for ev in events {
                self.refuse_private(&ev.to_toml()?)?;
            }
            let mut all = match hex {
                Some(h) => self.read_events_at(h, *id)?,
                None => Vec::new(),
            };
            all.extend(events.iter().cloned());
            let ticket = fold(*id, &all)?.ticket;
            titles.push(ticket.front.title.clone());
            changes.push((
                RelPath::new(format!("{dir}/{id}/ticket.md"))?,
                Some(crate::doc::render(&ticket)?.into_bytes()),
            ));
            for ev in events {
                changes.push((
                    RelPath::new(format!("{dir}/{id}/events/{}", ev.file_name()))?,
                    Some(ev.to_toml()?.into_bytes()),
                ));
            }
        }
        let message = match (planned, titles.first()) {
            ([(id, _)], Some(title)) => format!(
                "tickets(triage-{}): ~{} {title}",
                req.action,
                &id.random_part()[..7]
            ),
            _ => format!("tickets(triage-{}): {} tickets", req.action, planned.len()),
        };
        let ref_name = self.ledger_ref()?;
        let opts = CommitOptions {
            cas_retries: self.cfg.cas_retries,
            author: None,
        };
        let out = self
            .repo
            .commit_paths(&ref_name, &changes, &message, &opts)?;
        tracing::info!(action = %req.action, tickets = planned.len(), commit = %out.oid, retries = out.retries, "triage commit");
        if out.retries > 0 {
            // A concurrent writer moved the ref: re-fold any ticket that gained a foreign event.
            for (id, _) in planned {
                self.reconcile_with(&ref_name, *id, crate::ledger::MAX_RECONCILE)?;
            }
        }
        let warnings = crate::ledger::unsynced_warnings(&out.unsynced);
        Ok((out.oid, warnings))
    }

    /// The triage inbox at instant `at`: tickets in triage matching `filter`, snoozed ones hidden until their date unless `all`.
    ///
    /// Only `filter.label` and `filter.ty` are meaningful; the category is always triage.
    ///
    /// # Errors
    ///
    /// Store failures.
    pub fn inbox(&self, filter: &ListFilter, at: Stamp, all: bool) -> Result<Vec<InboxEntry>> {
        let s = self.synced()?;
        let rows = s.index.list(&ListFilter {
            category: Some(Category::Triage),
            ..filter.clone()
        })?;
        let mut out = Vec::new();
        for summary in rows {
            let events = match s.tip {
                Some(t) => self.read_events_at(&t.to_string(), summary.id)?,
                None => Vec::new(),
            };
            let snoozed_until = latest_triage(&events)
                .filter(|d| d.action == TriageAction::Snooze)
                .and_then(|d| d.until)
                .filter(|u| u.unix() > at.unix());
            if snoozed_until.is_some() && !all {
                tracing::debug!(ticket = %summary.id, "inbox hides a snoozed ticket");
                continue;
            }
            out.push(InboxEntry {
                summary,
                snoozed_until,
            });
        }
        Ok(out)
    }
}

/// The category and outcome a decision moves a ticket to (`None` for a snooze).
const fn destination(action: TriageAction) -> Option<(Category, Option<Outcome>)> {
    match action {
        TriageAction::Accept => Some((Category::Todo, None)),
        TriageAction::Decline => Some((Category::Done, Some(Outcome::WontFix))),
        TriageAction::Duplicate => Some((Category::Done, Some(Outcome::Duplicate))),
        TriageAction::Snooze => None,
    }
}

/// A report line for the unchanged ticket; the caller overrides the fields a decision changes.
fn entry(s: &Summary, status: TriageStatus) -> TriageEntry {
    TriageEntry {
        id: s.id,
        handle: s.handle.clone(),
        title: s.title.clone(),
        status,
        category: s.category,
        outcome: s.outcome,
    }
}

/// Check the request carries what its action needs.
fn validate(req: &TriageRequest, now: Stamp) -> Result<()> {
    let reasoned = req.reason.as_deref().is_some_and(|r| !r.trim().is_empty());
    match req.action {
        TriageAction::Decline if !reasoned => {
            return Err(LedgerError::invalid("decline needs a non-empty --reason"));
        }
        TriageAction::Duplicate if req.target.is_none() => {
            return Err(LedgerError::invalid("duplicate needs --of <ticket>"));
        }
        TriageAction::Snooze => match req.until {
            None => return Err(LedgerError::invalid("snooze needs --until <date>")),
            Some(u) if u.unix() <= now.unix() => {
                return Err(LedgerError::invalid(format!(
                    "--until {u} is not in the future (now is {now})"
                )));
            }
            Some(_) => {}
        },
        TriageAction::Accept | TriageAction::Decline | TriageAction::Duplicate => {}
    }
    Ok(())
}
