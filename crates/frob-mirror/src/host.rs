//! The concrete [`RunHost`] (mirror.md 3.1 to 3.4): wires the change feed, the outbox,
//! `create_issue`, `recover`, reconcile and duplicate closing behind the run driver.
//!
//! The ledger side (what tickets exist, their projections and events, where proposals are
//! committed) is the [`TicketSource`] seam; the tracker side is the adapter and the read sources.
//! The driver owns the store and the adapter and lends them to the host for each call, so the
//! host holds neither.

// frob:ticket 01M5EA0YFAACDY5BV70R2MH98S

use std::cell::RefCell;
use std::collections::{BTreeMap, BTreeSet};

use frob_ledger::event::Event;
use gob_time::Stamp;
use tracing::{debug, info, warn};

use crate::adapter::{AdapterError, EventId, IssueRef, IssueState, TrackerAdapter};
use crate::budget::RateLimit;
use crate::create::{CreateError, CreateStep, Recovery, RecoveryEnv, create_issue, recover};
use crate::cursor::{Committed, PendingCursor, begin_read};
use crate::dups::{DupReport, claims_from_verdicts, close_duplicates, plan_duplicates};
use crate::feed::{FeedSource, OBSERVED_UPDATED_AT, read_feed, select_for_history};
use crate::fields::FieldOwnership;
use crate::github::lookup::ListingSource;
use crate::github::read::{HistorySource, creation_revision};
use crate::journal::{read_journal, value_digest, write_journal};
use crate::keyring::Keyring;
use crate::lock::LedgerCommit;
use crate::mapfile::{MapError, Shard, ShardStore, read_shard, write_shard};
use crate::marker::evaluate;
use crate::normalize::ReadBack;
use crate::outbox::{
    FieldSink, LedgerEvent, Mode, OpOutcome, SinkError, apply_op, load_shards, plan_ops,
};
use crate::plan::{WorkClass, WorkItem};
use crate::progress::read_index;
use crate::projection::IssueProjection;
use crate::proposals::{ProposalSink, record};
use crate::reconcile::{IssueView, reconcile_issue};
use crate::run::{ItemError, RunHost};

/// Feed start used when the index holds no change-feed cursor yet.
const EPOCH: &str = "1970-01-01T00:00:00Z";

/// What reconcile needs of one ticket from the ledger side.
#[derive(Debug, Clone, Default)]
pub struct TicketState {
    /// The rendered projection, field to value.
    pub projection: BTreeMap<String, String>,
    /// Full values of tracker events the tracker retained, by event id.
    pub event_values: BTreeMap<EventId, String>,
    /// The ticket's ledger events, for proposal idempotency.
    pub existing: Vec<Event>,
    /// The stored read-back record for normalized comparison.
    pub read_back: ReadBack,
}

/// The ledger side of the mirror: which tickets exist and where outside edits are recorded.
pub trait TicketSource {
    /// Every mirrored ticket ULID: the sweep universe.
    fn mirrored(&self) -> Vec<String>;
    /// Tickets that should have an issue, each with an age key (lower is older).
    fn creatable(&self) -> Vec<(String, u64)>;
    /// The issue projection of `ulid`, or `None` when it cannot be rendered.
    fn projection(&self, ulid: &str) -> Option<IssueProjection>;
    /// All ledger events that carry projected field values, oldest first.
    fn events(&self) -> Vec<LedgerEvent>;
    /// Reconcile inputs for `ulid`, or `None` when the ticket is unknown.
    fn state(&self, ulid: &str) -> Option<TicketState>;
    /// The tracker's current field values of `state`, field to value.
    fn current(&self, state: &IssueState) -> BTreeMap<String, String>;
    /// Commits the proposal events recorded for `ulid` in one ledger commit.
    ///
    /// # Errors
    /// Returns a message when the commit fails; nothing is then considered recorded.
    fn commit_proposals(&mut self, ulid: &str, events: Vec<Event>) -> Result<(), String>;
    /// The ledger commit log, oldest first, the mirror's own commits flagged.
    fn commits(&self) -> Vec<LedgerCommit>;
}

/// Static settings of one host.
#[derive(Debug, Clone)]
pub struct HostConfig {
    /// Identity of the run; seeds create nonces.
    pub run_id: String,
    /// Unix time (seconds) now.
    pub now: i64,
    /// Create-start time, RFC 3339 UTC.
    pub started: String,
    /// Mirror bot user ids; the first is the creator whose issues are listed.
    pub bot_ids: Vec<u64>,
    /// Repository node id the marker MAC is bound to.
    pub repo_node_id: String,
    /// Remaining tracker calls and reset, read at run start.
    pub rate_limit: RateLimit,
    /// Outbox mode.
    pub mode: Mode,
    /// Most outbox ops per ticket per item.
    pub max_ops: usize,
    /// Most proposals recorded per reconcile (the per-run cap P).
    pub proposals_per_run: usize,
    /// Actor named on recorded proposals.
    pub actor: String,
}

/// The tracker-side readers the host consults.
pub struct Sources<'a> {
    /// The change feed.
    pub feed: &'a dyn FeedSource,
    /// The bot's issue listing.
    pub listing: &'a dyn ListingSource,
    /// Raw issue reads.
    pub history: &'a dyn HistorySource,
    /// Keyring verifying marker MACs.
    pub ring: &'a Keyring,
    /// Field ownership from `[mirror.fields]`.
    pub ownership: &'a FieldOwnership,
}

/// The [`RunHost`] over the real mirror modules.
pub struct MirrorHost<'a, T, K> {
    tickets: T,
    sink: K,
    src: Sources<'a>,
    cfg: HostConfig,
    seen: RefCell<BTreeMap<String, String>>,
    feed_cursor: RefCell<Option<String>>,
}

fn item_error(e: &AdapterError) -> ItemError {
    match e {
        AdapterError::RateLimited => ItemError::RateLimited { reset: None },
        other => ItemError::Failed(other.to_string()),
    }
}

fn create_error(e: &CreateError) -> ItemError {
    match e {
        CreateError::Tracker(a) => item_error(a),
        other => ItemError::Failed(other.to_string()),
    }
}

fn map_error(e: &MapError) -> ItemError {
    ItemError::Failed(e.to_string())
}

/// Adapts a [`TicketSource`] commit for one ticket to a [`ProposalSink`].
struct LedgerSink<'a, T> {
    tickets: &'a mut T,
    ulid: &'a str,
}

impl<T: TicketSource> ProposalSink for LedgerSink<'_, T> {
    type Error = String;

    /// Commits the ticket's proposals through the ledger seam.
    fn commit(&mut self, events: Vec<Event>) -> Result<(), String> {
        self.tickets.commit_proposals(self.ulid, events)
    }
}

impl<'a, T, K> MirrorHost<'a, T, K>
where
    T: TicketSource,
    K: FieldSink,
{
    /// Builds a host; the store and adapter arrive with each call from the driver.
    pub fn new(tickets: T, sink: K, src: Sources<'a>, cfg: HostConfig) -> Self {
        Self {
            tickets,
            sink,
            src,
            cfg,
            seen: RefCell::new(BTreeMap::new()),
            feed_cursor: RefCell::new(None),
        }
    }

    fn universe(&self) -> BTreeSet<String> {
        let mut all: BTreeSet<String> = self.tickets.mirrored().into_iter().collect();
        all.extend(self.tickets.creatable().into_iter().map(|(u, _)| u));
        all
    }

    fn shards<S: ShardStore>(&self, store: &S) -> BTreeMap<String, Shard> {
        load_shards(store, &self.universe()).unwrap_or_else(|e| {
            warn!(error = %e, "host: shards unreadable, no work planned");
            BTreeMap::new()
        })
    }

    fn load<S: ShardStore>(store: &S, ulid: &str) -> Result<Shard, ItemError> {
        read_shard(store, ulid)
            .map_err(|e| map_error(&e))
            .map(|s| s.unwrap_or_else(|| Shard::new(ulid)))
    }

    fn reconcile_items<S: ShardStore>(
        &self,
        store: &S,
        shards: &BTreeMap<String, Shard>,
    ) -> Vec<WorkItem> {
        let by_issue: BTreeMap<String, &Shard> = shards
            .values()
            .filter_map(|s| s.issue_number.map(|n| (n.to_string(), s)))
            .collect();
        let since = read_index(store)
            .ok()
            .and_then(|i| i.change_feed)
            .unwrap_or_else(|| EPOCH.to_owned());
        let feed = match read_feed(self.src.feed, &since) {
            Ok(f) => f,
            Err(e) => {
                warn!(error = %e, "host: feed unreadable, reconcile left to the sweep");
                return Vec::new();
            }
        };
        self.feed_cursor.replace(feed.cursor.clone());
        let lookup = |i: &IssueRef| by_issue.get(&i.0).map(|s| (*s).clone());
        let mut items = Vec::new();
        for (age, f) in select_for_history(&feed, &lookup).into_iter().enumerate() {
            let Some(shard) = by_issue.get(&f.issue.0) else {
                debug!(issue = %f.issue.0, "host: feed issue is not a mirrored ticket");
                continue;
            };
            self.seen
                .borrow_mut()
                .insert(shard.ulid.clone(), f.updated_at.clone());
            items.push(WorkItem {
                class: WorkClass::Reconcile,
                age: u64::try_from(age).unwrap_or(u64::MAX),
                ticket: shard.ulid.clone(),
            });
        }
        items
    }

    fn do_recover<S: ShardStore>(
        &self,
        store: &mut S,
        ulid: &str,
    ) -> Result<Option<Shard>, ItemError> {
        let shard = Self::load(store, ulid)?;
        let env = RecoveryEnv {
            listing: self.src.listing,
            source: self.src.history,
            ring: self.src.ring,
            bot_ids: &self.cfg.bot_ids,
            repo_node_id: &self.cfg.repo_node_id,
            now: self.cfg.now,
        };
        match recover(store, &env, shard).map_err(|e| create_error(&e))? {
            Recovery::Adopted(s) | Recovery::NotLanded(s) | Recovery::Nothing(s) => Ok(Some(s)),
        }
    }

    fn do_update<S: ShardStore>(
        &mut self,
        store: &mut S,
        ulid: &str,
    ) -> Result<Option<Shard>, ItemError> {
        let mut shard = Self::load(store, ulid)?;
        let one = BTreeMap::from([(ulid.to_owned(), shard.clone())]);
        let ops: Vec<LedgerEvent> = plan_ops(
            &self.tickets.events(),
            &one,
            self.cfg.mode,
            None,
            self.cfg.max_ops,
        )
        .into_iter()
        .filter(|o| o.ticket == ulid)
        .collect();
        let mut moved = false;
        for op in &ops {
            match apply_op(op, &mut shard, &mut self.sink) {
                OpOutcome::Applied | OpOutcome::Skipped => moved = true,
                OpOutcome::Deferred => break,
                OpOutcome::Failed => {
                    return Err(ItemError::Failed(format!("outbox op {} failed", op.key())));
                }
                OpOutcome::RateLimited { reset } => {
                    if moved {
                        Self::persist(store, &shard)?;
                    }
                    return Err(ItemError::RateLimited { reset });
                }
            }
        }
        info!(ulid, ops = ops.len(), moved, "host: outbox applied");
        Ok(moved.then_some(shard))
    }

    fn persist<S: ShardStore>(store: &mut S, shard: &Shard) -> Result<(), ItemError> {
        write_shard(store, shard)
            .map(|_| ())
            .map_err(|e| map_error(&e))
    }

    fn do_create<S: ShardStore>(
        &self,
        store: &mut S,
        adapter: &mut dyn TrackerAdapter,
        ulid: &str,
    ) -> Result<Option<Shard>, ItemError> {
        let Some(projection) = self.tickets.projection(ulid) else {
            warn!(ulid, "host: ticket cannot be rendered, create skipped");
            return Ok(None);
        };
        let shard = Self::load(store, ulid)?;
        let step = create_issue(
            store,
            adapter,
            shard,
            &projection,
            &self.cfg.run_id,
            &self.cfg.started,
            PendingCursor::empty(),
        )
        .map_err(|e| create_error(&e))?;
        match step {
            CreateStep::Created(made) => made
                .store_cursor(store, Committed::confirm())
                .map(Some)
                .map_err(|e| create_error(&e)),
            CreateStep::Uncertain(s) | CreateStep::Blocked(s) => Ok(Some(s)),
            CreateStep::Rejected(_, reason) => Err(ItemError::Failed(reason)),
        }
    }

    fn do_reconcile<S: ShardStore>(
        &mut self,
        store: &mut S,
        adapter: &dyn TrackerAdapter,
        ulid: &str,
    ) -> Result<Option<Shard>, ItemError> {
        let mut shard = Self::load(store, ulid)?;
        let (Some(number), Some(state)) = (shard.issue_number, self.tickets.state(ulid)) else {
            debug!(ulid, "host: no issue or no ledger state, reconcile skipped");
            return Ok(None);
        };
        let issue = IssueRef(number.to_string());
        let read = begin_read(self.src.history, &issue, &shard).map_err(|e| item_error(&e))?;
        let tracker = adapter.read(&issue).map_err(|e| item_error(&e))?;
        let current = self.tickets.current(&tracker);
        let mut journal = read_journal(store, ulid).map_err(|e| map_error(&e))?;
        let recovered = journal
            .recover(|_, field| Ok(value_digest(current.get(field).map_or("", String::as_str))));
        if recovered.confirmed + recovered.lost > 0
            && let Err(e) = write_journal(store, ulid, &journal)
        {
            warn!(ulid, error = %e, "host: journal recovery not stored");
        }
        let reconciled = reconcile_issue(&IssueView {
            issue: &issue,
            ownership: self.src.ownership,
            projection: &state.projection,
            current: &current,
            history: &read.history,
            event_values: &state.event_values,
            journal: &journal,
            bot_ids: &self.cfg.bot_ids,
            read_back: &state.read_back,
            now: Stamp::from_unix(self.cfg.now),
        });
        let mut advance = true;
        for revert in &reconciled.reverts {
            match self.sink.set_field(number, &revert.field, &revert.value) {
                Ok(normalized) => {
                    shard.observed.insert(revert.field.clone(), normalized);
                }
                Err(SinkError::RateLimited { reset }) => {
                    return Err(ItemError::RateLimited { reset });
                }
                Err(e) => {
                    warn!(ulid, field = %revert.field, error = %e, "host: revert failed");
                    advance = false;
                }
            }
        }
        let recorded = record(
            &mut LedgerSink {
                tickets: &mut self.tickets,
                ulid,
            },
            &state.existing,
            &reconciled.edits,
            &self.cfg.actor,
            Stamp::from_unix(self.cfg.now),
            self.cfg.proposals_per_run,
        )
        .map_err(ItemError::Failed)?;
        if advance && recorded.deferred == 0 {
            shard = read
                .pending
                .advance(shard, recorded.committed.unwrap_or_else(Committed::confirm));
            if let Some(at) = self.seen.borrow().get(ulid) {
                shard
                    .observed
                    .insert(OBSERVED_UPDATED_AT.to_owned(), at.clone());
            }
        }
        info!(
            ulid,
            reverts = reconciled.reverts.len(),
            proposals = recorded.appended,
            "host: reconciled"
        );
        Ok(Some(shard))
    }

    /// Closes the duplicate issues of this run's bot listing, keeping the lowest-numbered.
    ///
    /// The run driver calls this once per run through `RunHost::after_items`; a listing failure is returned and a
    /// per-issue marker read failure leaves that issue unclaimed until the next run.
    ///
    /// # Errors
    /// Returns the adapter's error when the bot's issues cannot be listed.
    pub fn close_duplicates(
        &self,
        adapter: &mut dyn TrackerAdapter,
    ) -> Result<DupReport, AdapterError> {
        let Some(&bot) = self.cfg.bot_ids.first() else {
            return Ok(DupReport::default());
        };
        let mut verdicts = Vec::new();
        for s in adapter.list_by_creator(bot)? {
            match creation_revision(self.src.history, &s.issue, s.creator_id) {
                Ok(c) => {
                    let v = evaluate(
                        &c,
                        &self.cfg.bot_ids,
                        self.src.ring,
                        &self.cfg.repo_node_id,
                        self.cfg.now,
                    );
                    verdicts.push((s.issue, v));
                }
                Err(e) => warn!(issue = %s.issue.0, error = %e, "host: creation unreadable"),
            }
        }
        let plan = plan_duplicates(&claims_from_verdicts(verdicts));
        let report = close_duplicates(adapter, &plan);
        info!(
            closed = report.closed.len(),
            failed = report.failed.len(),
            "host: duplicates handled"
        );
        Ok(report)
    }
}

impl<T, K> RunHost for MirrorHost<'_, T, K>
where
    T: TicketSource,
    K: FieldSink,
{
    /// The limit read at run start.
    fn rate_limit(&self) -> RateLimit {
        self.cfg.rate_limit
    }

    /// The newest update time the feed read saw, for the driver to persist as the cursor.
    fn feed_cursor(&self) -> Option<String> {
        self.feed_cursor.borrow().clone()
    }

    /// The ledger seam's commit log, so the run can advance its watermark.
    fn ledger_commits(&self) -> Vec<LedgerCommit> {
        self.tickets.commits()
    }

    /// Recovery, update, create and reconcile work; the driver adds the sweep.
    fn pending<S: ShardStore>(&self, store: &S) -> Vec<WorkItem> {
        let shards = self.shards(store);
        let item = |class, age: u64, ticket: &str| WorkItem {
            class,
            age,
            ticket: ticket.to_owned(),
        };
        let mut items: Vec<WorkItem> = shards
            .values()
            .filter(|s| s.create_uncertain.is_some())
            .map(|s| item(WorkClass::Recovery, 0, &s.ulid))
            .collect();
        let ops = plan_ops(
            &self.tickets.events(),
            &shards,
            self.cfg.mode,
            None,
            self.cfg.max_ops,
        );
        let mut seen = BTreeSet::new();
        for op in ops {
            if shards
                .get(&op.ticket)
                .is_some_and(|s| s.issue_number.is_some())
                && seen.insert(op.ticket.clone())
            {
                items.push(item(
                    WorkClass::Update,
                    u64::try_from(seen.len()).unwrap_or(u64::MAX),
                    &op.ticket,
                ));
            }
        }
        for (ulid, age) in self.tickets.creatable() {
            let has = shards
                .get(&ulid)
                .is_some_and(|s| s.issue_number.is_some() || s.create_uncertain.is_some());
            if !has {
                items.push(item(WorkClass::Create, age, &ulid));
            }
        }
        items.extend(self.reconcile_items(store, &shards));
        debug!(items = items.len(), "host: pending work");
        items
    }

    /// Every mirrored ticket, for the sweep.
    fn sweep_universe(&self) -> Vec<String> {
        self.tickets.mirrored()
    }

    /// Runs one item against the tracker and returns the shard to record.
    fn execute<S: ShardStore>(
        &mut self,
        item: &WorkItem,
        store: &mut S,
        adapter: &mut dyn TrackerAdapter,
    ) -> Result<Option<Shard>, ItemError> {
        let ulid = item.ticket.as_str();
        debug!(ulid, class = ?item.class, "host: executing");
        match item.class {
            WorkClass::Recovery => self.do_recover(store, ulid),
            WorkClass::Update => self.do_update(store, ulid),
            WorkClass::Create => self.do_create(store, adapter, ulid),
            WorkClass::Reconcile | WorkClass::Sweep => self.do_reconcile(store, adapter, ulid),
        }
    }

    /// Closes this run's duplicate issues; a listing failure is logged and retried next run.
    fn after_items(&mut self, adapter: &mut dyn TrackerAdapter) {
        if let Err(e) = self.close_duplicates(adapter) {
            warn!(error = %e, "host: duplicate check failed, retried next run");
        }
    }
}
