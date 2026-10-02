//! Ledger operations: the mutations and queries behind the ticket verbs.

use std::collections::BTreeSet;

use gob_git::Oid;
use schemars::JsonSchema;
use serde::Serialize;

use crate::error::{LedgerError, Result};
use crate::event::{
    CommentData, CreateData, Event, EventBody, FieldChange, LinkData, TransitionData,
};
use crate::guards::{CloseContext, CloseGuard, LeaseCheck};
use crate::id::{EventId, TicketId};
use crate::index::{ListFilter, Summary};
use crate::ledger::{Applied, Ledger, Synced};
use crate::links::{Edge, check_add, check_parent};
use crate::model::{
    Category, CommentSubtype, Link, LinkKind, LinkOp, Outcome, Points, Priority, Ticket, TicketType,
};
use crate::schema::{get_field, set_field};

/// A request to create a ticket.
#[derive(Debug, Clone)]
pub struct NewTicket {
    /// Title (required, non-empty).
    pub title: String,
    /// Ticket type.
    pub ty: TicketType,
    /// Starting category: `triage` or `todo`.
    pub category: Category,
    /// Priority.
    pub priority: Priority,
    /// Story points.
    pub points: Option<Points>,
    /// Parent ticket (must exist).
    pub parent: Option<TicketId>,
    /// Tickets that block this one (must exist).
    pub blocked_by: Vec<TicketId>,
    /// Scope globs.
    pub scope: Vec<String>,
    /// Labels.
    pub labels: Vec<String>,
    /// Acceptance criteria.
    pub acceptance: Vec<String>,
    /// Markdown body.
    pub body: String,
    /// Idempotency key: the same key returns the same ticket.
    pub idempotency_key: Option<String>,
    /// Story persona.
    pub persona: Option<String>,
    /// Story capability.
    pub capability: Option<String>,
    /// Story outcome text.
    pub outcome_text: Option<String>,
    /// Flavour.
    pub flavour: Option<String>,
    /// Assignee.
    pub assignee: Option<String>,
    /// Aliases (v1 ids).
    pub aliases: Vec<String>,
}

impl NewTicket {
    /// A request with `title` and `ty`, medium priority, category `todo`, all else empty.
    pub fn new(title: impl Into<String>, ty: TicketType) -> Self {
        Self {
            title: title.into(),
            ty,
            category: Category::Todo,
            priority: Priority::Medium,
            points: None,
            parent: None,
            blocked_by: Vec::new(),
            scope: Vec::new(),
            labels: Vec::new(),
            acceptance: Vec::new(),
            body: String::new(),
            idempotency_key: None,
            persona: None,
            capability: None,
            outcome_text: None,
            flavour: None,
            assignee: None,
            aliases: Vec::new(),
        }
    }
}

/// A patch for `update`: field sets plus label edits.
#[derive(Debug, Clone, Default)]
pub struct Patch {
    /// `(field, new value)`; `None` unsets an optional field.
    pub sets: Vec<(String, Option<toml::Value>)>,
    /// Labels to add.
    pub add_labels: Vec<String>,
    /// Labels to remove.
    pub remove_labels: Vec<String>,
    /// Reason recorded on the events (required when changing `flavour`).
    pub reason: Option<String>,
}

/// A link as shown on a ticket.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct LinkView {
    /// Kind, spelled from the shown ticket's side.
    pub kind: LinkKind,
    /// The other ticket.
    pub id: TicketId,
    /// Its handle, or `None` when it does not exist (dangling).
    pub handle: Option<String>,
    /// Its title.
    pub title: Option<String>,
    /// Its category.
    pub category: Option<Category>,
}

/// Everything `show` reports about a ticket.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TicketView {
    /// The index row.
    pub summary: Summary,
    /// The full document.
    pub ticket: Ticket,
    /// Links stored on this ticket.
    pub outgoing: Vec<LinkView>,
    /// Links stored on other tickets that point here, spelled from this side.
    pub incoming: Vec<LinkView>,
    /// Tickets whose parent is this one.
    pub children: Vec<Summary>,
}

impl Ledger {
    /// Resolve a full ULID, `~suffix` handle or alias to one ticket.
    ///
    /// # Errors
    ///
    /// [`LedgerError::NotFound`], [`LedgerError::Ambiguous`] or a store failure.
    pub fn resolve(&self, input: &str) -> Result<TicketId> {
        self.synced()?.index.resolve(input)
    }

    /// Summaries matching `filter`, from the index.
    ///
    /// # Errors
    ///
    /// Store failures.
    pub fn list(&self, filter: &ListFilter) -> Result<Vec<Summary>> {
        self.synced()?.index.list(filter)
    }

    /// Tickets in `todo` with no open blocker whose scope is lease-free.
    ///
    /// Epics are excluded: they cannot be worked directly (tickets.md section 3).
    ///
    /// # Errors
    ///
    /// Store failures.
    pub fn doable(&self, lease: &dyn LeaseCheck) -> Result<Vec<Summary>> {
        let s = self.synced()?;
        let candidates = s.index.list(&ListFilter {
            category: Some(Category::Todo),
            blocked: Some(false),
            ..ListFilter::default()
        })?;
        let mut out = Vec::new();
        for c in candidates {
            if c.ty == TicketType::Epic {
                continue;
            }
            let scope = s
                .index
                .get(c.id)?
                .map(|t| t.front.scope)
                .unwrap_or_default();
            if lease.is_free(&c, &scope) {
                out.push(c);
            } else {
                tracing::debug!(ticket = %c.id, "excluded from doable by lease check");
            }
        }
        Ok(out)
    }

    /// The full view of ticket `id`.
    ///
    /// # Errors
    ///
    /// [`LedgerError::NotFound`] or store failures.
    pub fn show(&self, id: TicketId) -> Result<TicketView> {
        let s = self.synced()?;
        let (summary, ticket) = Self::load(&s, id)?;
        let describe = |kind: LinkKind, other: TicketId| -> Result<LinkView> {
            let found = s.index.summary(other)?;
            Ok(LinkView {
                kind,
                id: other,
                handle: found.as_ref().map(|x| x.handle.clone()),
                title: found.as_ref().map(|x| x.title.clone()),
                category: found.as_ref().map(|x| x.category),
            })
        };
        let outgoing = ticket
            .front
            .links
            .iter()
            .map(|l| describe(l.kind, l.target))
            .collect::<Result<Vec<_>>>()?;
        let incoming = s
            .index
            .incoming(id)?
            .into_iter()
            .map(|(k, src)| describe(k, src))
            .collect::<Result<Vec<_>>>()?;
        let children = s.index.list(&ListFilter {
            parent: Some(id),
            ..ListFilter::default()
        })?;
        Ok(TicketView {
            summary,
            ticket,
            outgoing,
            incoming,
            children,
        })
    }

    /// The events of ticket `id` at the ledger tip, in fold order.
    ///
    /// # Errors
    ///
    /// [`LedgerError::NotFound`] when the ticket is absent, or store failures.
    pub fn events(&self, id: TicketId) -> Result<Vec<Event>> {
        let s = self.synced()?;
        Self::load(&s, id)?;
        match s.tip {
            Some(tip) => self.read_events_at(&tip.to_string(), id),
            None => Ok(Vec::new()),
        }
    }

    fn load(s: &Synced, id: TicketId) -> Result<(Summary, Ticket)> {
        let not_found = || LedgerError::NotFound {
            input: id.to_string(),
        };
        let summary = s.index.summary(id)?.ok_or_else(not_found)?;
        let ticket = s.index.get(id)?.ok_or_else(not_found)?;
        Ok((summary, ticket))
    }

    fn already(s: &Synced, id: TicketId) -> Result<Applied> {
        let (summary, ticket) = Self::load(s, id)?;
        Ok(Applied {
            ticket,
            handle: summary.handle,
            events: Vec::new(),
            already: true,
            commit: None,
        })
    }

    fn require_exists(s: &Synced, id: TicketId) -> Result<()> {
        if s.index.summary(id)?.is_some() {
            Ok(())
        } else {
            Err(LedgerError::NotFound {
                input: id.to_string(),
            })
        }
    }

    /// Create a ticket; a repeated idempotency key returns the first ticket with `already`.
    ///
    /// # Errors
    ///
    /// [`LedgerError::Invalid`] for an empty title or a category other than
    /// triage or todo, [`LedgerError::NotFound`] for a missing parent or
    /// blocker, plus git and store failures.
    pub fn new_ticket(&self, req: NewTicket) -> Result<Applied> {
        let s = self.synced()?;
        if let Some(key) = &req.idempotency_key
            && let Some(id) = s.index.find_by_key(key)?
        {
            tracing::info!(ticket = %id, key, "idempotent new returned the existing ticket");
            return Self::already(&s, id);
        }
        if req.title.trim().is_empty() {
            return Err(LedgerError::invalid("a ticket needs a non-empty title"));
        }
        if !matches!(req.category, Category::Triage | Category::Todo) {
            return Err(LedgerError::invalid(
                "a new ticket starts in triage or todo",
            ));
        }
        if let Some(p) = req.parent {
            Self::require_exists(&s, p)?;
        }
        for b in &req.blocked_by {
            Self::require_exists(&s, *b)?;
        }
        let mut links: Vec<Link> = req
            .blocked_by
            .iter()
            .map(|t| Link {
                kind: LinkKind::BlockedBy,
                target: *t,
            })
            .collect();
        links.sort();
        links.dedup();
        let actor = self.actor()?;
        let id = TicketId::mint();
        let event = Event::new(
            &actor,
            EventBody::Create(Box::new(CreateData {
                title: req.title.trim().to_owned(),
                ty: req.ty,
                category: req.category,
                priority: req.priority,
                flavour: req.flavour,
                points: req.points,
                parent: req.parent,
                assignee: req.assignee,
                persona: req.persona,
                capability: req.capability,
                outcome_text: req.outcome_text,
                idempotency_key: req.idempotency_key,
                aliases: req.aliases,
                labels: dedup(req.labels),
                scope: req.scope,
                acceptance: req.acceptance,
                body: req.body,
                links,
            })),
        );
        drop(s);
        self.commit_events("new", id, &[event])
    }

    /// Apply a patch to ticket `id`; an empty effective patch is `already`.
    ///
    /// # Errors
    ///
    /// [`LedgerError::Invalid`] for unknown, unsettable or mistyped fields, a
    /// `flavour` change without a reason, or an empty title;
    /// [`LedgerError::LinkRejected`] for a parent cycle; plus lookup and store failures.
    pub fn update(&self, id: TicketId, patch: &Patch) -> Result<Applied> {
        let s = self.synced()?;
        let (_, current) = Self::load(&s, id)?;
        let actor = self.actor()?;
        let mut work = current;
        let mut events = Vec::new();
        for (name, new) in &patch.sets {
            let old = get_field(&work, name);
            if old == *new {
                continue;
            }
            if name == "title"
                && new
                    .as_ref()
                    .and_then(toml::Value::as_str)
                    .is_none_or(|t| t.trim().is_empty())
            {
                return Err(LedgerError::invalid("a ticket needs a non-empty title"));
            }
            if name == "flavour" && patch.reason.as_deref().is_none_or(str::is_empty) {
                return Err(LedgerError::invalid("changing flavour needs --reason"));
            }
            if name == "parent"
                && let Some(p) = new.as_ref().and_then(toml::Value::as_str)
            {
                let parent: TicketId = p
                    .parse()
                    .map_err(|e: crate::id::ParseIdError| LedgerError::invalid(e.to_string()))?;
                Self::require_exists(&s, parent)?;
                let parent_of =
                    |t: TicketId| s.index.summary(t).ok().flatten().and_then(|x| x.parent);
                check_parent(&parent_of, id, parent)?;
            }
            set_field(&mut work, name, new.as_ref()).map_err(LedgerError::invalid)?;
            events.push(Event::new(
                &actor,
                EventBody::Field(FieldChange {
                    field: name.clone(),
                    old,
                    new: new.clone(),
                    reason: patch.reason.clone(),
                }),
            ));
        }
        if !patch.add_labels.is_empty() || !patch.remove_labels.is_empty() {
            let mut labels = work.front.labels.clone();
            labels.retain(|l| !patch.remove_labels.contains(l));
            for l in &patch.add_labels {
                if !labels.contains(l) {
                    labels.push(l.clone());
                }
            }
            if labels != work.front.labels {
                let old = get_field(&work, "labels");
                let new = (!labels.is_empty()).then(|| {
                    toml::Value::Array(labels.iter().cloned().map(toml::Value::String).collect())
                });
                events.push(Event::new(
                    &actor,
                    EventBody::Field(FieldChange {
                        field: "labels".to_owned(),
                        old,
                        new,
                        reason: patch.reason.clone(),
                    }),
                ));
            }
        }
        if events.is_empty() {
            return Self::already(&s, id);
        }
        drop(s);
        self.commit_events("update", id, &events)
    }

    /// Add the link `id --kind--> target`; an existing edge (either spelling) is `already`.
    ///
    /// # Errors
    ///
    /// [`LedgerError::LinkRejected`] for a self link, cycle, second origin,
    /// duplicate-of-duplicate or a non-story `enabler-for` target;
    /// [`LedgerError::NotFound`] for a missing ticket; plus store failures.
    pub fn link(&self, id: TicketId, kind: LinkKind, target: TicketId) -> Result<Applied> {
        let s = self.synced()?;
        Self::load(&s, id)?;
        Self::require_exists(&s, target)?;
        let edges = s.index.edges()?;
        if edges.contains(&Edge::normalize(id, kind, target)) {
            return Self::already(&s, id);
        }
        let ty_of = |t: TicketId| s.index.summary(t).ok().flatten().map(|x| x.ty);
        check_add(&edges, &ty_of, id, kind, target)?;
        let actor = self.actor()?;
        let event = Event::new(
            &actor,
            EventBody::Link(LinkData {
                op: LinkOp::Add,
                link: kind,
                target,
            }),
        );
        drop(s);
        self.commit_events("link", id, &[event])
    }

    /// Remove the link `id --kind--> target`, wherever either spelling is stored.
    ///
    /// # Errors
    ///
    /// [`LedgerError::NotFound`] for a missing ticket, plus store failures.
    pub fn unlink(&self, id: TicketId, kind: LinkKind, target: TicketId) -> Result<Applied> {
        let s = self.synced()?;
        let (_, here) = Self::load(&s, id)?;
        let there = s.index.get(target)?;
        let direct = Link { kind, target };
        let (owner, kind_stored, other) = if here.front.links.contains(&direct) {
            (id, kind, target)
        } else if let Some(t) = there
            && t.front.links.contains(&Link {
                kind: kind.inverse(),
                target: id,
            })
        {
            (target, kind.inverse(), id)
        } else {
            return Self::already(&s, id);
        };
        let actor = self.actor()?;
        let event = Event::new(
            &actor,
            EventBody::Link(LinkData {
                op: LinkOp::Remove,
                link: kind_stored,
                target: other,
            }),
        );
        drop(s);
        self.commit_events("unlink", owner, &[event])
    }

    /// Add a comment event to ticket `id`.
    ///
    /// # Errors
    ///
    /// [`LedgerError::Invalid`] for an empty body, [`LedgerError::NotFound`], or store failures.
    pub fn comment(&self, id: TicketId, subtype: CommentSubtype, body: &str) -> Result<Applied> {
        if body.trim().is_empty() {
            return Err(LedgerError::invalid("a comment needs a non-empty body"));
        }
        let s = self.synced()?;
        Self::load(&s, id)?;
        let event = Event::new(
            &self.actor()?,
            EventBody::Comment(CommentData {
                subtype,
                body: body.to_owned(),
            }),
        );
        drop(s);
        self.commit_events("comment", id, &[event])
    }

    /// Move `id` to `to` (a general transition for lease and workflow crates).
    ///
    /// Moving to `done` needs an outcome and bypasses close guards; use
    /// [`Ledger::close`] for the guarded path. A ticket already in `to` is `already`.
    ///
    /// # Errors
    ///
    /// [`LedgerError::Invalid`] when the outcome does not match `to`, plus lookup and store failures.
    pub fn transition(
        &self,
        id: TicketId,
        to: Category,
        outcome: Option<Outcome>,
        reason: Option<String>,
    ) -> Result<Applied> {
        self.transition_as("transition", id, to, outcome, reason)
    }

    /// [`Ledger::transition`] with the verb name used in the commit message.
    fn transition_as(
        &self,
        verb: &str,
        id: TicketId,
        to: Category,
        outcome: Option<Outcome>,
        reason: Option<String>,
    ) -> Result<Applied> {
        if (to == Category::Done) != outcome.is_some() {
            return Err(LedgerError::invalid(
                "an outcome goes with a move to done and with nothing else",
            ));
        }
        let s = self.synced()?;
        let (_, current) = Self::load(&s, id)?;
        if current.front.category == to && current.front.outcome == outcome {
            return Self::already(&s, id);
        }
        let event = Event::new(
            &self.actor()?,
            EventBody::Transition(TransitionData {
                from: current.front.category,
                to,
                outcome,
                reason,
            }),
        );
        drop(s);
        self.commit_events(verb, id, &[event])
    }

    /// Close `id` with `outcome` after every guard passes; a repeat is `already`.
    ///
    /// # Errors
    ///
    /// [`LedgerError::GuardRefused`] when a guard refuses,
    /// [`LedgerError::Terminal`] when the ticket is done with another outcome,
    /// plus lookup and store failures.
    pub fn close(
        &self,
        id: TicketId,
        outcome: Option<Outcome>,
        reason: Option<String>,
        guards: &[&dyn CloseGuard],
    ) -> Result<Applied> {
        self.close_as("close", id, outcome, reason, guards)
    }

    fn close_as(
        &self,
        verb: &str,
        id: TicketId,
        outcome: Option<Outcome>,
        reason: Option<String>,
        guards: &[&dyn CloseGuard],
    ) -> Result<Applied> {
        let s = self.synced()?;
        let (summary, current) = Self::load(&s, id)?;
        if current.front.category == Category::Done {
            return match (outcome, current.front.outcome) {
                (None, _) => Self::already(&s, id),
                (Some(a), Some(b)) if a == b => Self::already(&s, id),
                (Some(a), b) => Err(LedgerError::Terminal {
                    message: format!(
                        "{} is already done with outcome {}; it cannot become {a}",
                        summary.handle,
                        b.map_or("none", Outcome::as_str)
                    ),
                }),
            };
        }
        let cx = CloseContext {
            ticket: &current,
            handle: &summary.handle,
            outcome,
        };
        for g in guards {
            if let Err(f) = g.check(&cx) {
                tracing::info!(ticket = %id, guard = g.name(), code = %f.code, "close guard refused");
                return Err(LedgerError::GuardRefused {
                    code: f.code,
                    message: f.message,
                    remedy: f.remedy,
                });
            }
        }
        let outcome = outcome.ok_or_else(|| LedgerError::GuardRefused {
            code: "E-CLOSE-OUTCOME".to_owned(),
            message: format!("closing {} needs an outcome", summary.handle),
            remedy: Some(format!(
                "frob ticket close {} --outcome done",
                summary.handle
            )),
        })?;
        drop(s);
        self.transition_as(verb, id, Category::Done, Some(outcome), reason)
    }

    /// Drop `id`: close with outcome `wont-fix` and a required reason.
    ///
    /// # Errors
    ///
    /// [`LedgerError::Invalid`] without a reason, [`LedgerError::Terminal`] when
    /// already done with another outcome, plus lookup and store failures.
    pub fn drop_ticket(&self, id: TicketId, reason: &str) -> Result<Applied> {
        if reason.trim().is_empty() {
            return Err(LedgerError::invalid("drop needs a non-empty --reason"));
        }
        self.close_as(
            "drop",
            id,
            Some(Outcome::WontFix),
            Some(reason.to_owned()),
            &[],
        )
    }

    /// Reopen a done ticket into `todo`; a ticket that is not done is `already`.
    ///
    /// # Errors
    ///
    /// [`LedgerError::Invalid`] without a reason, plus lookup and store failures.
    pub fn reopen(&self, id: TicketId, reason: &str) -> Result<Applied> {
        if reason.trim().is_empty() {
            return Err(LedgerError::invalid("reopen needs a non-empty --reason"));
        }
        let s = self.synced()?;
        let (_, current) = Self::load(&s, id)?;
        if current.front.category != Category::Done {
            return Self::already(&s, id);
        }
        drop(s);
        self.transition_as("reopen", id, Category::Todo, None, Some(reason.to_owned()))
    }

    /// Markdown brief of ticket `id`: title, body, acceptance, scope, links and recent events.
    ///
    /// # Errors
    ///
    /// [`LedgerError::NotFound`] or store failures.
    pub fn brief(&self, id: TicketId) -> Result<String> {
        let view = self.show(id)?;
        let events = self.events(id)?;
        Ok(crate::brief::render(&view, &events))
    }

    /// All ticket ids at the ledger tip (not the index): the ground truth for doctor and rules.
    ///
    /// # Errors
    ///
    /// Store failures.
    pub fn ticket_ids(&self) -> Result<BTreeSet<TicketId>> {
        let ref_name = self.ledger_ref()?;
        let Some(tip) = self.tip_of(&ref_name)? else {
            return Ok(BTreeSet::new());
        };
        Ok(self.ticket_ids_at(&tip.to_string())?.into_iter().collect())
    }

    /// The commit the ledger ref currently points at.
    ///
    /// # Errors
    ///
    /// Store failures.
    pub fn tip(&self) -> Result<Option<Oid>> {
        let ref_name = self.ledger_ref()?;
        self.tip_of(&ref_name)
    }

    /// Event ids written by a mutation, as strings (convenience for envelopes).
    pub fn event_strings(events: &[EventId]) -> Vec<String> {
        events.iter().map(ToString::to_string).collect()
    }
}

fn dedup(mut v: Vec<String>) -> Vec<String> {
    let mut seen = BTreeSet::new();
    v.retain(|s| seen.insert(s.clone()));
    v
}
