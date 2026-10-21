//! The ledger-side [`TicketSource`]: the mirror host's view of a real `frob_ledger::Ledger`.
//!
//! Evidence folding lives in the `frob` crate, so the caller injects a [`FactsFn`] that builds
//! the [`TicketFacts`] of one ticket; everything else (map shards, events, commit log,
//! proposal commits) is read from and written to the ledger here.

// frob:ticket 01M5EBMAWCRQ2S1GGPYACC0466

use std::collections::{BTreeMap, BTreeSet};

use frob_ledger::event::{Event, EventBody};
use frob_ledger::{Ledger, TicketId};
use tracing::{debug, info, warn};

use crate::adapter::IssueState;
use crate::host::{TicketSource, TicketState};
use crate::lock::LedgerCommit;
use crate::normalize::ReadBack;
use crate::outbox::LedgerEvent;
use crate::projection::{IssueProjection, TicketFacts, project};

/// Builds the facts of one ticket, or `None` when it cannot be folded.
pub type FactsFn<'a> = Box<dyn Fn(&Ledger, TicketId) -> Option<TicketFacts> + 'a>;

/// Subject prefix of the commits the mirror itself authors (proposal events).
const OWN_SUBJECT: &str = "tickets(proposal";

/// Field name of the ticket title in projections and ledger events.
pub const FIELD_TITLE: &str = "title";
/// Field name of the labels list (comma-joined, sorted).
pub const FIELD_LABELS: &str = "labels";
/// Field name of the assignee list (comma-joined, sorted).
pub const FIELD_ASSIGNEE: &str = "assignee";
/// Field name of the open/closed state.
pub const FIELD_STATE: &str = "state";

/// A [`TicketSource`] over a real ledger.
pub struct LedgerTickets<'a> {
    ledger: &'a Ledger,
    facts: FactsFn<'a>,
    exclude: BTreeSet<String>,
    producer_version: String,
}

impl<'a> LedgerTickets<'a> {
    /// A source over `ledger` rendering projections with `facts`, withholding `exclude`.
    pub fn new(
        ledger: &'a Ledger,
        facts: FactsFn<'a>,
        exclude: BTreeSet<String>,
        producer_version: &str,
    ) -> Self {
        Self {
            ledger,
            facts,
            exclude,
            producer_version: producer_version.to_owned(),
        }
    }

    /// Every ticket id, logging and yielding none when the ledger cannot be read.
    fn ids(&self) -> Vec<TicketId> {
        match self.ledger.ticket_ids() {
            Ok(ids) => ids.into_iter().collect(),
            Err(e) => {
                warn!(error = %e, "ledger tickets unreadable");
                Vec::new()
            }
        }
    }

    /// The mapped issue number of `id`, `None` when unmapped or unreadable.
    fn issue_of(&self, id: TicketId) -> Option<u64> {
        match self.ledger.mirror_issue(id) {
            Ok(n) => n,
            Err(e) => {
                warn!(ticket = %id, error = %e, "mirror shard unreadable");
                None
            }
        }
    }
}

/// Joins a string list as the sorted comma-separated field value.
fn join_sorted(items: &[String]) -> String {
    let mut v: Vec<&str> = items.iter().map(String::as_str).collect();
    v.sort_unstable();
    v.join(",")
}

/// Renders a ledger field value the way [`field_map`] renders the projection.
fn render_value(v: &toml::Value) -> String {
    match v {
        toml::Value::String(s) => s.clone(),
        toml::Value::Array(a) => {
            let items: Vec<String> = a
                .iter()
                .map(|x| x.as_str().map_or_else(|| x.to_string(), str::to_owned))
                .collect();
            join_sorted(&items)
        }
        other => other.to_string(),
    }
}

/// The projected field values of `p`, field to value.
fn field_map(p: &IssueProjection) -> BTreeMap<String, String> {
    let mut m = BTreeMap::new();
    m.insert(FIELD_TITLE.to_owned(), p.title.clone());
    m.insert(
        FIELD_STATE.to_owned(),
        state_word(p.state.category == crate::projection::Category::Done).to_owned(),
    );
    if let Some(l) = &p.classification.labels {
        m.insert(FIELD_LABELS.to_owned(), join_sorted(l));
    }
    if let Some(a) = &p.people.assignee {
        m.insert(FIELD_ASSIGNEE.to_owned(), a.clone());
    }
    m
}

/// The state field value for a closed or open ticket.
const fn state_word(closed: bool) -> &'static str {
    if closed { "closed" } else { "open" }
}

/// The projected-field events carried by one ledger `event` of `ticket`.
fn ledger_events(ticket: TicketId, event: &Event) -> Option<LedgerEvent> {
    let (field, value) = match &event.body {
        EventBody::Create(c) => (FIELD_TITLE.to_owned(), c.title.clone()),
        EventBody::Field(f)
            if matches!(
                f.field.as_str(),
                FIELD_TITLE | FIELD_LABELS | FIELD_ASSIGNEE
            ) =>
        {
            (f.field.clone(), f.new.as_ref().map(render_value)?)
        }
        EventBody::Transition(t) => (
            FIELD_STATE.to_owned(),
            state_word(t.to.is_terminal()).to_owned(),
        ),
        _ => return None,
    };
    Some(LedgerEvent {
        ticket: ticket.to_string(),
        event: event.id.to_string(),
        field,
        value,
    })
}

impl TicketSource for LedgerTickets<'_> {
    fn mirrored(&self) -> Vec<String> {
        let out: Vec<String> = self
            .ids()
            .into_iter()
            .filter(|id| self.issue_of(*id).is_some())
            .map(|id| id.to_string())
            .collect();
        debug!(count = out.len(), "mirrored tickets listed");
        out
    }

    fn creatable(&self) -> Vec<(String, u64)> {
        let out: Vec<(String, u64)> = self
            .ids()
            .into_iter()
            .filter(|id| self.issue_of(*id).is_none())
            .map(|id| (id.to_string(), id.timestamp_ms()))
            .collect();
        debug!(count = out.len(), "creatable tickets listed");
        out
    }

    fn projection(&self, ulid: &str) -> Option<IssueProjection> {
        let id: TicketId = ulid.parse().ok()?;
        let Some(facts) = (self.facts)(self.ledger, id) else {
            debug!(ticket = ulid, "no facts; projection unavailable");
            return None;
        };
        Some(project(&facts, &self.exclude, &self.producer_version))
    }

    fn events(&self) -> Vec<LedgerEvent> {
        let ids: BTreeSet<TicketId> = self.ids().into_iter().collect();
        let all = match self.ledger.events_many(&ids) {
            Ok(a) => a,
            Err(e) => {
                warn!(error = %e, "ledger events unreadable");
                return Vec::new();
            }
        };
        let mut out: Vec<LedgerEvent> = all
            .iter()
            .flat_map(|(id, evs)| evs.iter().filter_map(|e| ledger_events(*id, e)))
            .collect();
        out.sort_by(|a, b| a.event.cmp(&b.event));
        debug!(count = out.len(), "projected-field ledger events listed");
        out
    }

    fn state(&self, ulid: &str) -> Option<TicketState> {
        let id: TicketId = ulid.parse().ok()?;
        let projection = self.projection(ulid)?;
        let existing = match self.ledger.events(id) {
            Ok(e) => e,
            Err(e) => {
                warn!(ticket = ulid, error = %e, "ticket events unreadable");
                return None;
            }
        };
        // Retained tracker event values and the read-back record are not persisted in the
        // ledger map shard yet; reconcile falls back to the current tracker value.
        Some(TicketState {
            projection: field_map(&projection),
            event_values: BTreeMap::new(),
            existing,
            read_back: ReadBack::new(),
        })
    }

    fn current(&self, state: &IssueState) -> BTreeMap<String, String> {
        let mut m = BTreeMap::new();
        m.insert(FIELD_TITLE.to_owned(), state.title.clone());
        m.insert(FIELD_STATE.to_owned(), state_word(state.closed).to_owned());
        m.insert(FIELD_LABELS.to_owned(), join_sorted(&state.labels));
        m.insert(FIELD_ASSIGNEE.to_owned(), join_sorted(&state.assignees));
        m
    }

    fn commit_proposals(&mut self, ulid: &str, events: Vec<Event>) -> Result<(), String> {
        let id: TicketId = ulid.parse().map_err(|_| format!("bad ticket id {ulid}"))?;
        for ev in events {
            // The ledger appends one event per commit; a failure leaves earlier ones recorded,
            // which proposal idempotency (keyed by tracker event) tolerates on retry.
            self.ledger.append(id, ev.body).map_err(|e| {
                warn!(ticket = ulid, error = %e, "proposal commit failed");
                e.to_string()
            })?;
        }
        info!(ticket = ulid, "proposals recorded in the ledger");
        Ok(())
    }

    fn commits(&self) -> Vec<LedgerCommit> {
        let read = self
            .ledger
            .ledger_ref()
            .map_err(|e| e.to_string())
            .and_then(|r| {
                self.ledger
                    .repo()
                    .first_parent_commits(&r, usize::MAX)
                    .map_err(|e| e.to_string())
            });
        match read {
            Ok(mut commits) => {
                commits.reverse();
                commits
                    .into_iter()
                    .map(|c| LedgerCommit {
                        id: c.id.to_string(),
                        own: c.message.starts_with(OWN_SUBJECT),
                    })
                    .collect()
            }
            Err(e) => {
                warn!(error = %e, "ledger commit log unreadable");
                Vec::new()
            }
        }
    }
}
