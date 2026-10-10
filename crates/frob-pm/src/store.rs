//! [`PmStore`]: milestones and cycles read from and appended to the ledger.
//!
//! Layout (releases.md section 6a), below the ledger's tickets directory:
//! `_milestones/<ULID>/milestone.md` and `_cycles/<ULID>/cycle.md` hold the
//! frontmatter, `events/<ULID>.toml` one event each. Every write is one ledger
//! commit through [`Ledger::commit_files`] holding the new event files and the
//! re-folded frontmatter, so `fold(events) == frontmatter` after every commit.
//! Nothing here touches a ticket: membership is an event on the object.
// frob:ticket 01M40VQWCV38B2JCABYNNNA877

use std::collections::BTreeMap;

use frob_ledger::event::{EvidenceData, FieldChange};
use frob_ledger::{EventId, Ledger, TicketId};

use crate::cycle::lifecycle::state_on;
use crate::error::{PmError, Result};
use crate::event::{
    CreateData, CriterionData, MemberData, Op, PmBody, PmEvent, TransitionData, sort_events,
};
use crate::fold::{Folded, fold, get_field};
use crate::model::{Day, Object, ObjectId, ObjectKind, State};

const MAX_RECONCILE: u32 = 3;

/// What to create: a milestone or a cycle with its initial values.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NewObject {
    /// A milestone.
    Milestone {
        /// Version, also the alias.
        version: String,
        /// One-line goal.
        goal: String,
        /// Target date; `None` is unscheduled.
        target: Option<Day>,
        /// Initial exit criteria.
        criteria: Vec<String>,
    },
    /// A cycle.
    Cycle {
        /// First day.
        start: Day,
        /// Last day.
        end: Day,
        /// One-line goal.
        goal: String,
        /// Committed story points.
        capacity_points: Option<u32>,
    },
}

impl NewObject {
    fn into_create(self) -> CreateData {
        match self {
            Self::Milestone {
                version,
                goal,
                target,
                criteria,
            } => CreateData {
                object: ObjectKind::Milestone,
                version: Some(version),
                goal,
                target,
                start: None,
                end: None,
                capacity_points: None,
                criteria,
                ordinal: None,
            },
            Self::Cycle {
                start,
                end,
                goal,
                capacity_points,
            } => CreateData {
                object: ObjectKind::Cycle,
                version: None,
                goal,
                target: None,
                start: Some(start),
                end: Some(end),
                capacity_points,
                criteria: Vec::new(),
                ordinal: None,
            },
        }
    }
}

/// A committed change to one object.
#[derive(Debug, Clone)]
pub struct Applied {
    /// The object after the change (the fold at the new tip).
    pub object: Object,
    /// Ids of the events written.
    pub events: Vec<EventId>,
    /// The ledger commit (hex).
    pub commit: String,
}

/// Milestones and cycles of one [`Ledger`].
#[derive(Debug, Clone, Copy)]
pub struct PmStore<'a> {
    pub(crate) ledger: &'a Ledger,
}

impl<'a> PmStore<'a> {
    /// A store over `ledger`.
    pub fn new(ledger: &'a Ledger) -> Self {
        Self { ledger }
    }

    /// The ledger underneath.
    pub fn ledger(self) -> &'a Ledger {
        self.ledger
    }

    /// Repo-relative directory holding every object of `kind`.
    pub(crate) fn kind_dir(self, kind: ObjectKind) -> String {
        format!("{}{}", self.ledger.tree_prefix(), kind.dir())
    }

    /// Repo-relative directory of one object.
    pub fn object_dir(self, kind: ObjectKind, id: ObjectId) -> String {
        format!("{}/{id}", self.kind_dir(kind))
    }

    /// Names of every object directory of `kind` at `tip` (valid ULIDs or not), sorted.
    pub(crate) fn dir_names(self, tip: &str, kind: ObjectKind) -> Result<Vec<String>> {
        let mut names: Vec<String> = self
            .ledger
            .list_files_below(tip, &self.kind_dir(kind))?
            .iter()
            .filter_map(|p| p.split_once('/').map(|(d, _)| d.to_owned()))
            .collect();
        names.sort();
        names.dedup();
        Ok(names)
    }

    /// Ids of the objects of `kind` at `tip` whose directory name is a ULID.
    ///
    /// # Errors
    ///
    /// Ledger read failures.
    pub fn ids_at(self, tip: &str, kind: ObjectKind) -> Result<Vec<ObjectId>> {
        Ok(self
            .dir_names(tip, kind)?
            .iter()
            .filter_map(|n| n.parse().ok())
            .collect())
    }

    /// Read every event of one object at `tip`, in fold order.
    ///
    /// # Errors
    ///
    /// Ledger read failures or a malformed event file.
    pub fn read_events_at(self, tip: &str, kind: ObjectKind, id: ObjectId) -> Result<Vec<PmEvent>> {
        let dir = format!("{}/events", self.object_dir(kind, id));
        let mut events = Vec::new();
        for name in self.ledger.list_files_below(tip, &dir)? {
            let Some(eid) = name
                .strip_suffix(".toml")
                .and_then(|s| s.parse::<EventId>().ok())
            else {
                tracing::warn!(object = %id, file = %name, "ignoring non-event file in events/");
                continue;
            };
            let path = format!("{dir}/{name}");
            let text = self
                .ledger
                .read_text_at(tip, &path)?
                .ok_or_else(|| PmError::malformed(&path, "listed but unreadable"))?;
            events.push(PmEvent::parse(eid, &text).map_err(|e| match e {
                PmError::Malformed { message, .. } => PmError::malformed(&path, message),
                other => other,
            })?);
        }
        sort_events(&mut events);
        Ok(events)
    }

    /// The stored frontmatter of one object at `tip` (the cache, not the fold).
    ///
    /// # Errors
    ///
    /// Ledger read failures or a malformed file.
    pub fn read_stored_at(
        self,
        tip: &str,
        kind: ObjectKind,
        id: ObjectId,
    ) -> Result<Option<Object>> {
        let path = format!("{}/{}", self.object_dir(kind, id), kind.file());
        self.ledger
            .read_text_at(tip, &path)?
            .map(|t| Object::parse(kind, &path, &t))
            .transpose()
    }

    /// Fold one object from its events at the current tip; `None` when it has no events.
    ///
    /// # Errors
    ///
    /// Ledger read failures, a malformed event or a failing fold.
    pub fn get(self, kind: ObjectKind, id: ObjectId) -> Result<Option<Folded>> {
        let Some(tip) = self.ledger.tip_hex()? else {
            return Ok(None);
        };
        let events = self.read_events_at(&tip, kind, id)?;
        if events.is_empty() {
            return Ok(None);
        }
        Ok(Some(fold(kind, id, &events)?))
    }

    /// The ordinal a new cycle of `start..end` takes: one above the highest already used by that range.
    fn next_ordinal(self, start: Day, end: Day) -> Result<u32> {
        let highest = self
            .list(ObjectKind::Cycle)?
            .iter()
            .filter_map(|o| match o {
                Object::Cycle(c) if c.start == start && c.end == end => Some(c.ordinal),
                _ => None,
            })
            .max()
            .unwrap_or(0);
        tracing::debug!(%start, %end, highest, "next cycle ordinal chosen");
        Ok(highest + 1)
    }

    /// Every object of `kind` folded at the current tip, ordered by id; unreadable ones are skipped with a warning.
    ///
    /// # Errors
    ///
    /// Ledger read failures.
    pub fn list(self, kind: ObjectKind) -> Result<Vec<Object>> {
        let Some(tip) = self.ledger.tip_hex()? else {
            return Ok(Vec::new());
        };
        let mut out = Vec::new();
        for id in self.ids_at(&tip, kind)? {
            match self
                .read_events_at(&tip, kind, id)
                .and_then(|e| fold(kind, id, &e))
            {
                Ok(f) => out.push(f.object),
                Err(e) => tracing::warn!(object = %id, error = %e, "skipping unreadable object"),
            }
        }
        Ok(out)
    }

    /// Resolve a reference to one object: a full ULID, a `~suffix` handle, or the alias (version or dates).
    ///
    /// # Errors
    ///
    /// [`PmError::NotFound`], [`PmError::Ambiguous`] or ledger read failures.
    pub fn resolve(self, kind: ObjectKind, reference: &str) -> Result<Object> {
        let upper = reference.to_ascii_uppercase();
        let suffix = upper.strip_prefix('~');
        let mut hits: Vec<Object> = self
            .list(kind)?
            .into_iter()
            .filter(|o| {
                let id = o.id().to_string();
                id == upper
                    || o.alias() == reference
                    || suffix.is_some_and(|s| !s.is_empty() && id.ends_with(s))
            })
            .collect();
        match hits.len() {
            0 => Err(PmError::NotFound {
                kind,
                reference: reference.to_owned(),
            }),
            1 => Ok(hits.remove(0)),
            count => Err(PmError::Ambiguous {
                kind,
                reference: reference.to_owned(),
                count,
            }),
        }
    }

    /// Today's UTC day on the ledger's clock: the one day every judgement of this command uses.
    pub fn today(self) -> Day {
        self.ledger.clock().today()
    }

    /// Create a milestone or cycle: one `create` event and its frontmatter in one commit.
    ///
    /// # Errors
    ///
    /// [`PmError::Invalid`] for a bad date range, a missing version, or an alias
    /// (version, dates) that another object of the kind already has; ledger failures.
    pub fn create(self, new: NewObject) -> Result<Applied> {
        let mut data = new.into_create();
        let kind = data.object;
        let id = ObjectId::mint();
        // frob:ticket 01M41KS5P8EGFFGBQSMRFBAJ8P
        // The suffix is fixed here, once, so no two cycles of a range ever share an alias.
        if let (ObjectKind::Cycle, Some(start), Some(end)) = (kind, data.start, data.end) {
            let ordinal = self.next_ordinal(start, end)?;
            data.ordinal = (ordinal > 1).then_some(ordinal);
        }
        let event = PmEvent::new(
            self.ledger.clock().now(),
            &self.ledger.actor()?,
            PmBody::Create(Box::new(data)),
        );
        let folded = fold(kind, id, std::slice::from_ref(&event))?;
        let alias = folded.object.alias();
        // A closed cycle never holds its date range: only open or planned cycles (and any milestone) block the alias.
        let taken = |o: &Object| match (o, &folded.object) {
            (Object::Cycle(c), Object::Cycle(n)) => {
                c.state != State::Closed && c.start == n.start && c.end == n.end
            }
            _ => o.alias() == alias,
        };
        if self.list(kind)?.iter().any(taken) {
            return Err(PmError::invalid(format!(
                "a {kind} `{alias}` already exists"
            )));
        }
        tracing::info!(object = %id, %kind, %alias, "creating");
        self.commit(kind, id, &[event])
    }

    /// Append one event of an already-validated `body` to an existing object.
    ///
    /// The fold of the history plus the new event must succeed or nothing is written.
    ///
    /// # Errors
    ///
    /// [`PmError::Invalid`] for a `create` or uninterpreted body, [`PmError::NotFound`],
    /// [`PmError::Fold`] when the event does not fold, and ledger failures.
    pub fn append(self, kind: ObjectKind, id: ObjectId, body: PmBody) -> Result<Applied> {
        if matches!(body, PmBody::Create(_) | PmBody::Other) {
            return Err(PmError::invalid(
                "append takes an interpreted, non-create event body",
            ));
        }
        let event = PmEvent::new(self.ledger.clock().now(), &self.ledger.actor()?, body);
        self.commit(kind, id, &[event])
    }

    /// Append several already-validated event bodies to an existing object in one commit, in the order given.
    ///
    /// The fold of the history plus all of them must succeed or nothing is written.
    ///
    /// # Errors
    ///
    /// As [`PmStore::append`].
    pub fn append_many(
        self,
        kind: ObjectKind,
        id: ObjectId,
        bodies: Vec<PmBody>,
    ) -> Result<Applied> {
        if bodies
            .iter()
            .any(|b| matches!(b, PmBody::Create(_) | PmBody::Other))
        {
            return Err(PmError::invalid(
                "append takes interpreted, non-create event bodies",
            ));
        }
        let actor = self.ledger.actor()?;
        let events: Vec<PmEvent> = bodies
            .into_iter()
            .map(|b| PmEvent::new(self.ledger.clock().now(), &actor, b))
            .collect();
        self.commit(kind, id, &events)
    }

    /// Change one frontmatter field (`new` of `None` unsets it); the previous value is recorded for conflict detection.
    ///
    /// # Errors
    ///
    /// As [`PmStore::append`].
    pub fn set_field(
        self,
        kind: ObjectKind,
        id: ObjectId,
        field: &str,
        new: Option<toml::Value>,
    ) -> Result<Applied> {
        let current = self.require(kind, id)?;
        let old = get_field(&current.object, field);
        self.append(
            kind,
            id,
            PmBody::Field(FieldChange {
                field: field.to_owned(),
                old,
                new,
                reason: None,
                moved: None,
            }),
        )
    }

    /// Add or remove a member ticket; `None` when it already holds (nothing written).
    ///
    /// # Errors
    ///
    /// As [`PmStore::append`].
    pub fn set_member(
        self,
        kind: ObjectKind,
        id: ObjectId,
        ticket: TicketId,
        op: Op,
    ) -> Result<Option<Applied>> {
        let current = self.require(kind, id)?;
        let is_member = current.object.members().contains(&ticket);
        if is_member == (op == Op::Add) {
            tracing::debug!(object = %id, %ticket, ?op, "membership already holds");
            return Ok(None);
        }
        self.append(kind, id, PmBody::Member(MemberData { op, ticket }))
            .map(Some)
    }

    /// Add an exit criterion to a milestone.
    ///
    /// # Errors
    ///
    /// As [`PmStore::append`].
    pub fn add_criterion(self, id: ObjectId, text: &str) -> Result<Applied> {
        self.append(
            ObjectKind::Milestone,
            id,
            PmBody::Criterion(CriterionData {
                op: Op::Add,
                text: Some(text.to_owned()),
                position: None,
                moved: None,
            }),
        )
    }

    /// Remove the exit criterion at 1-based `position` of a milestone.
    ///
    /// # Errors
    ///
    /// As [`PmStore::append`].
    pub fn remove_criterion(self, id: ObjectId, position: usize) -> Result<Applied> {
        let count = match self.require(ObjectKind::Milestone, id)?.object {
            Object::Milestone(m) => m.criteria.len(),
            Object::Cycle(_) => 0,
        };
        let moved = (1..=count)
            .map(|n| match n.cmp(&position) {
                std::cmp::Ordering::Less => n,
                std::cmp::Ordering::Equal => 0,
                std::cmp::Ordering::Greater => n - 1,
            })
            .collect();
        self.append(
            ObjectKind::Milestone,
            id,
            PmBody::Criterion(CriterionData {
                op: Op::Remove,
                text: None,
                position: Some(position),
                moved: Some(moved),
            }),
        )
    }

    /// Offer a measurement for exit criteria of a milestone (`data.accepts` are 1-based positions now).
    ///
    /// # Errors
    ///
    /// As [`PmStore::append`].
    pub fn add_evidence(self, id: ObjectId, data: EvidenceData) -> Result<Applied> {
        self.append(ObjectKind::Milestone, id, PmBody::Evidence(data))
    }

    /// Move an object to state `to`, recording the state it leaves.
    ///
    /// # Errors
    ///
    /// As [`PmStore::append`]; [`PmError::Fold`] when `to` is not a state of the kind.
    pub fn transition(
        self,
        kind: ObjectKind,
        id: ObjectId,
        to: State,
        reason: Option<String>,
    ) -> Result<Applied> {
        let current = self.require(kind, id)?;
        // frob:ticket 01M41KS5P8EGFFGBQSMRFBAJ8P
        let from = match &current.object {
            Object::Milestone(m) => m.state,
            Object::Cycle(c) => state_on(c, self.today()),
        };
        self.append(
            kind,
            id,
            PmBody::Transition(TransitionData {
                from,
                to,
                reason,
                ended: None,
            }),
        )
    }

    fn require(self, kind: ObjectKind, id: ObjectId) -> Result<Folded> {
        self.get(kind, id)?.ok_or(PmError::NotFound {
            kind,
            reference: id.to_string(),
        })
    }

    /// Commit `new` events of one object with its re-folded frontmatter, then reconcile concurrent writers.
    fn commit(self, kind: ObjectKind, id: ObjectId, new: &[PmEvent]) -> Result<Applied> {
        let creating = new.iter().any(|e| matches!(e.body, PmBody::Create(_)));
        let mut all = match (creating, self.ledger.tip_hex()?) {
            (false, Some(tip)) => self.read_events_at(&tip, kind, id)?,
            _ => Vec::new(),
        };
        if !creating && all.is_empty() {
            return Err(PmError::NotFound {
                kind,
                reference: id.to_string(),
            });
        }
        all.extend(new.iter().cloned());
        let folded = fold(kind, id, &all)?;
        let dir = self.object_dir(kind, id);
        let mut changes = vec![(
            format!("{dir}/{}", kind.file()),
            Some(folded.object.render()?.into_bytes()),
        )];
        for ev in new {
            tracing::debug!(object = %id, event = %ev.id, kind = ev.body.name(), "pm event written");
            changes.push((
                format!("{dir}/events/{}", ev.file_name()),
                Some(ev.to_toml()?.into_bytes()),
            ));
        }
        let verb = new.last().map_or("noop", |e| e.body.name());
        let message = format!(
            "tickets({kind}-{verb}): {} {}",
            id.handle(),
            folded.object.alias()
        );
        let commit = self.ledger.commit_files(&message, &changes)?.to_string();
        let object = self
            .reconcile(kind, id, MAX_RECONCILE)?
            .map_or(folded.object, |f| f.object);
        Ok(Applied {
            object,
            events: new.iter().map(|e| e.id).collect(),
            commit,
        })
    }

    /// Re-fold `id` at the tip and rewrite its frontmatter when a concurrent writer left it stale.
    ///
    /// Returns the fold at the final tip, or `None` when there is nothing there.
    ///
    /// # Errors
    ///
    /// Ledger, parse or fold failures.
    pub fn reconcile(
        self,
        kind: ObjectKind,
        id: ObjectId,
        attempts: u32,
    ) -> Result<Option<Folded>> {
        let mut last = None;
        for _ in 0..attempts {
            let Some(tip) = self.ledger.tip_hex()? else {
                return Ok(None);
            };
            let events = self.read_events_at(&tip, kind, id)?;
            if events.is_empty() {
                return Ok(None);
            }
            let folded = fold(kind, id, &events)?;
            if self.read_stored_at(&tip, kind, id)?.as_ref() == Some(&folded.object) {
                return Ok(Some(folded));
            }
            let path = format!("{}/{}", self.object_dir(kind, id), kind.file());
            let message = format!(
                "tickets({kind}-reconcile): {} re-fold frontmatter",
                id.handle()
            );
            let commit = self.ledger.commit_files(
                &message,
                &[(path, Some(folded.object.render()?.into_bytes()))],
            )?;
            tracing::info!(object = %id, %commit, "frontmatter reconciled");
            last = Some(folded);
        }
        Ok(last)
    }

    /// Group the files below a kind directory by object directory name.
    pub(crate) fn files_by_dir(
        self,
        tip: &str,
        kind: ObjectKind,
    ) -> Result<BTreeMap<String, Vec<String>>> {
        let mut out: BTreeMap<String, Vec<String>> = BTreeMap::new();
        for p in self.ledger.list_files_below(tip, &self.kind_dir(kind))? {
            if let Some((d, rest)) = p.split_once('/') {
                out.entry(d.to_owned()).or_default().push(rest.to_owned());
            }
        }
        Ok(out)
    }
}
