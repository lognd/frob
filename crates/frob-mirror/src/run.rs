//! The mirror run driver (mirror.md 3.1 to 3.4): lock, blindness, budget, work classes in strict
//! priority with the feed and the sweep, per-ticket isolation, progress commits and a report.
//!
//! The driver owns ordering and bookkeeping only; what one work item does to the tracker is the
//! host's `execute`, so a run over a converged state asks for no work and commits nothing.

// frob:ticket 01M4052W6Q1FAQK362YF6RCGW1

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use tracing::{debug, info, warn};

use crate::adapter::TrackerAdapter;
use crate::blind::check_blind;
use crate::budget::{self, BudgetConfig, RateLimit};
use crate::lock::{self, Acquire, LedgerCommit};
use crate::mapfile::{MapError, Shard, ShardStore, content_hash, decode, encode};
use crate::plan::{Cursors, WorkClass, WorkItem, select};
use crate::progress::{ProgressWriter, RunReport, StopReason};
use crate::sweep::next_batch;

/// Store key of the per-class round-robin cursors (F8).
pub const CURSORS_KEY: &str = "run-cursors";

/// Every work class, for walking the cursors.
const CLASSES: [WorkClass; 5] = [
    WorkClass::Recovery,
    WorkClass::Update,
    WorkClass::Create,
    WorkClass::Reconcile,
    WorkClass::Sweep,
];

/// The stable name a class is stored under.
fn class_name(class: WorkClass) -> &'static str {
    match class {
        WorkClass::Recovery => "recovery",
        WorkClass::Update => "update",
        WorkClass::Create => "create",
        WorkClass::Reconcile => "reconcile",
        WorkClass::Sweep => "sweep",
    }
}

/// One class's resume point as stored.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
struct StoredCursor {
    age: u64,
    ticket: String,
}

/// The stored record: last completed item per class name. Unknown names are ignored on read.
#[derive(Debug, Default, Serialize, Deserialize)]
struct CursorRecord {
    #[serde(default)]
    classes: BTreeMap<String, StoredCursor>,
}

/// Reads the persisted cursors; a missing record (a store from before F8) is all-default.
///
/// # Errors
/// `MapError::Corrupt` when the stored record does not decode.
// frob:ticket 01M5EWJDDGZS0G0346T3A6WZ0W
pub fn load_cursors<S: ShardStore>(store: &S) -> Result<Cursors, MapError> {
    let Some(bytes) = store.get(CURSORS_KEY) else {
        debug!("mirror run: no stored cursors, starting fresh");
        return Ok(Cursors::default());
    };
    let record: CursorRecord = decode(CURSORS_KEY, &bytes)?;
    let mut cursors = Cursors::default();
    for class in CLASSES {
        if let Some(c) = record.classes.get(class_name(class)) {
            cursors.complete(&WorkItem {
                class,
                age: c.age,
                ticket: c.ticket.clone(),
            });
        }
    }
    Ok(cursors)
}

/// Persists `cursors` by CAS so the next run resumes each class after its last completed item.
///
/// # Errors
/// `MapError::Conflict` when another writer changed the record first.
// frob:ticket 01M5EWJDDGZS0G0346T3A6WZ0W
pub fn save_cursors<S: ShardStore>(store: &mut S, cursors: &Cursors) -> Result<(), MapError> {
    let classes = CLASSES
        .into_iter()
        .filter_map(|c| {
            cursors.get(c).map(|(age, t)| {
                (
                    class_name(c).to_string(),
                    StoredCursor {
                        age,
                        ticket: t.to_string(),
                    },
                )
            })
        })
        .collect();
    let expected = store.get(CURSORS_KEY).map(|b| content_hash(&b));
    store.put_if(
        CURSORS_KEY,
        expected.as_deref(),
        encode(&CursorRecord { classes }),
    )?;
    debug!("mirror run: cursors saved");
    Ok(())
}

/// `cursors` minus the sweep: the sweep batch arrives already rotated by `next_batch`.
fn without_sweep(cursors: &Cursors) -> Cursors {
    let mut out = Cursors::default();
    for class in CLASSES.into_iter().filter(|c| *c != WorkClass::Sweep) {
        if let Some((age, t)) = cursors.get(class) {
            out.complete(&WorkItem {
                class,
                age,
                ticket: t.to_string(),
            });
        }
    }
    out
}

/// Settings of one run.
#[derive(Debug, Clone)]
pub struct RunConfig {
    /// Identity of this run, stored in the lock.
    pub run_id: String,
    /// Unix time (seconds) now.
    pub now: u64,
    /// Seconds after which another run's lock is stale.
    pub lock_ttl_secs: u64,
    /// Operations between progress commits.
    pub commit_every: u64,
    /// Issues the sweep reconciles per run.
    pub sweep_k: usize,
    /// Account id of the bot whose issues the blindness check lists.
    pub bot_id: u64,
    /// Budget shares and caps.
    pub budget: BudgetConfig,
}

/// Why one work item failed.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum ItemError {
    /// The tracker throttled the call: the whole run stops.
    #[error("rate limited")]
    RateLimited {
        /// Unix time the window resets, when known.
        reset: Option<u64>,
    },
    /// This ticket failed (for example it cannot be rendered); the others go on.
    #[error("{0}")]
    Failed(String),
}

/// What the run needs from its surroundings: the work to do and how to do one item.
pub trait RunHost {
    /// The current rate-limit headers.
    fn rate_limit(&self) -> RateLimit;
    /// Pending recovery, update, create and reconcile (feed) items; the driver adds the sweep.
    fn pending<S: ShardStore>(&self, store: &S) -> Vec<WorkItem>;
    /// Every mirrored ticket ULID, the sweep's universe.
    fn sweep_universe(&self) -> Vec<String>;
    /// The ledger commit log, oldest first, own commits flagged; empty when the host has none.
    fn ledger_commits(&self) -> Vec<LedgerCommit> {
        Vec::new()
    }
    /// The change-feed cursor read this run (update time of the newest issue seen), if any.
    fn feed_cursor(&self) -> Option<String> {
        None
    }
    /// Does one item against the driver's `store` and `adapter`; `Ok(None)` means nothing
    /// changed, `Ok(Some)` returns the shard to commit.
    ///
    /// # Errors
    /// `ItemError::RateLimited` stops the run; `ItemError::Failed` skips this ticket only.
    fn execute<S: ShardStore>(
        &mut self,
        item: &WorkItem,
        store: &mut S,
        adapter: &mut dyn TrackerAdapter,
    ) -> Result<Option<Shard>, ItemError>;
    /// Per-run housekeeping after the items ran and before the final commit (for example
    /// closing duplicate issues); a failure is the host's to log and never fails the run.
    fn after_items(&mut self, _adapter: &mut dyn TrackerAdapter) {}
}

/// How a run ended.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RunOutcome {
    /// A live run holds the lock: exit 0 without work.
    Busy {
        /// The live holder.
        holder: String,
    },
    /// Nothing ran; MIR001 explains why (token-blind or budget).
    Stopped {
        /// The MIR001 message.
        mir001: String,
    },
    /// The run executed.
    Ran(RunSummary),
}

/// The report of an executed run.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RunSummary {
    /// Progress commit report (committed operations, rate-limit MIR001).
    pub report: RunReport,
    /// Items executed, in order.
    pub executed: Vec<(WorkClass, String)>,
    /// Tickets that failed, with the reason; they never stopped the others.
    pub failed: Vec<(String, String)>,
    /// Foreign ledger commits seen after the watermark when the run began.
    pub new_commits: usize,
    /// The watermark after the run, when it was advanced.
    pub watermark: Option<String>,
}

/// Runs one mirror pass: lock, blindness, budget, classes in priority, commit, release.
///
/// # Errors
/// `MapError` when the store fails (corrupt record or lost CAS race).
pub fn run<S: ShardStore, H: RunHost>(
    store: &mut S,
    adapter: &mut dyn TrackerAdapter,
    host: &mut H,
    cfg: &RunConfig,
) -> Result<RunOutcome, MapError> {
    match lock::acquire(store, &cfg.run_id, cfg.now, cfg.lock_ttl_secs)? {
        Acquire::Busy { holder } => {
            info!(%holder, "mirror run: lock busy, exiting without work");
            return Ok(RunOutcome::Busy { holder });
        }
        Acquire::Held { .. } => {}
    }
    let outcome = run_locked(store, adapter, host, cfg);
    lock::release(store, &cfg.run_id)?;
    outcome
}

/// The run body, executed while the writer lock is held.
fn run_locked<S: ShardStore, H: RunHost>(
    store: &mut S,
    adapter: &mut dyn TrackerAdapter,
    host: &mut H,
    cfg: &RunConfig,
) -> Result<RunOutcome, MapError> {
    if let Err(e) = check_blind(&*adapter, cfg.bot_id) {
        let mir001 = e.to_string();
        warn!(%mir001, "mirror run: blind, nothing else runs");
        return Ok(RunOutcome::Stopped { mir001 });
    }
    let plan = match budget::plan(host.rate_limit(), &cfg.budget) {
        Ok(p) => p,
        Err(e) => {
            let mir001 = e.to_string();
            warn!(%mir001, "mirror run: no budget plan");
            return Ok(RunOutcome::Stopped { mir001 });
        }
    };
    let log = host.ledger_commits();
    let prior = lock::read_watermark(store)?;
    let new_commits = lock::pending_commits(prior.as_ref(), &log).len();
    debug!(
        new_commits,
        "mirror run: foreign ledger commits since watermark"
    );
    let stored = load_cursors(&*store)?;
    let mut writer = ProgressWriter::new(store, cfg.commit_every)?;
    let mut items = host.pending(writer.store());
    let universe = host.sweep_universe();
    // The sweep resumes after its own last completed ticket; stores from before F8 fall back to
    // the index cursor. Ages follow batch order so `select` keeps the order and a small budget
    // serves a prefix of the batch, which the next run continues from.
    let sweep_after = stored
        .get(WorkClass::Sweep)
        .map(|(_, t)| t.to_string())
        .or_else(|| writer.resume_after().map(String::from));
    items.extend(
        next_batch(&universe, sweep_after.as_deref(), cfg.sweep_k)
            .into_iter()
            .zip(0u64..)
            .map(|(ticket, age)| WorkItem {
                class: WorkClass::Sweep,
                age,
                ticket,
            }),
    );
    let planned: Vec<WorkClass> = items.iter().map(|i| i.class).collect();
    let cost = cfg.budget.reads_per_ticket + 1;
    let selected = select(items, &without_sweep(&stored), &plan, cost);
    debug!(selected = selected.len(), "mirror run: work selected");
    let (mut cursors, mut executed, mut failed) = (stored.clone(), Vec::new(), Vec::new());
    let mut stop = StopReason::Completed;
    for item in &selected {
        match host.execute(item, writer.store_mut(), &mut *adapter) {
            Ok(shard) => {
                if let Some(shard) = shard {
                    writer.record(shard)?;
                }
                cursors.complete(item);
                executed.push((item.class, item.ticket.clone()));
            }
            Err(ItemError::RateLimited { reset }) => {
                warn!(ticket = %item.ticket, "mirror run: rate limited, stopping");
                stop = StopReason::RateLimited { reset };
                break;
            }
            Err(ItemError::Failed(why)) => {
                warn!(ticket = %item.ticket, %why, "mirror run: ticket failed, others continue");
                failed.push((item.ticket.clone(), why));
            }
        }
    }
    if matches!(stop, StopReason::Completed) {
        host.after_items(&mut *adapter);
    }
    // The feed cursor moves only when every reconcile item was done: otherwise the unprocessed
    // issues would fall behind it and never be seen again.
    let count = |classes: &mut dyn Iterator<Item = WorkClass>| {
        classes.filter(|c| *c == WorkClass::Reconcile).count()
    };
    let all_reconciled =
        count(&mut planned.iter().copied()) == count(&mut executed.iter().map(|(c, _)| *c));
    let advance_feed = failed.is_empty() && matches!(stop, StopReason::Completed) && all_reconciled;
    if let Some(cursor) = host.feed_cursor().filter(|_| advance_feed) {
        writer.set_change_feed(cursor);
    }
    let report = writer.finish(stop)?;
    if cursors != stored {
        save_cursors(store, &cursors)?;
    }
    let watermark = advance_watermark(store, &log, prior.as_ref(), &stop, failed.is_empty())?;
    info!(
        executed = executed.len(),
        failed = failed.len(),
        "mirror run: finished"
    );
    Ok(RunOutcome::Ran(RunSummary {
        report,
        executed,
        failed,
        new_commits,
        watermark,
    }))
}

/// Advances the watermark to the log head after a clean, complete run; otherwise leaves it so
/// the unfinished commits are seen again. Returns the new watermark when it moved.
fn advance_watermark<S: ShardStore>(
    store: &mut S,
    log: &[LedgerCommit],
    prior: Option<&lock::Watermark>,
    stop: &StopReason,
    clean: bool,
) -> Result<Option<String>, MapError> {
    let Some(head) = log.last() else {
        return Ok(None);
    };
    if !clean || !matches!(stop, StopReason::Completed) {
        info!("mirror run: incomplete, watermark held");
        return Ok(None);
    }
    if prior.is_some_and(|w| w.commit == head.id) {
        return Ok(None);
    }
    lock::write_watermark(store, &head.id)?;
    info!(commit = %head.id, "mirror run: watermark advanced");
    Ok(Some(head.id.clone()))
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;
    use std::time::Duration;

    use super::*;
    use crate::adapter::{
        AdapterError, AdapterResult, Capabilities, CreateOutcome, EventId, HistoryEntry,
        HistoryRetention, Inventory, IssueRef, IssueState, IssueSummary, MarkdownDialect,
        StateReasons,
    };
    use crate::mapfile::content_hash;
    use crate::projection::{IssueProjection, Outcome, RelationKind};

    #[derive(Default)]
    struct Mem {
        data: HashMap<String, Vec<u8>>,
        puts: Vec<String>,
    }

    impl ShardStore for Mem {
        fn get(&self, key: &str) -> Option<Vec<u8>> {
            self.data.get(key).cloned()
        }
        fn put_if(&mut self, key: &str, exp: Option<&str>, bytes: Vec<u8>) -> Result<(), MapError> {
            let found = self.get(key).map(|b| content_hash(&b));
            if found.as_deref() != exp {
                return Err(MapError::Conflict {
                    key: key.into(),
                    expected: exp.map(String::from),
                    found,
                });
            }
            self.puts.push(key.into());
            self.data.insert(key.into(), bytes);
            Ok(())
        }
    }

    /// Offline adapter: visible or blind; only the blindness reads are exercised.
    struct Fake {
        visible: bool,
    }

    impl TrackerAdapter for Fake {
        fn capabilities(&self) -> Capabilities {
            Capabilities {
                native_sub_issues: false,
                native_links: false,
                custom_fields: false,
                state_reasons: StateReasons::Unsupported,
                history_retention: HistoryRetention::None,
                markdown: MarkdownDialect::Github,
            }
        }
        fn create(&mut self, _: &IssueProjection, _: &str) -> CreateOutcome {
            CreateOutcome::Unknown
        }
        fn update(&mut self, _: &IssueRef, _: &IssueProjection) -> AdapterResult<()> {
            Ok(())
        }
        fn close(&mut self, _: &IssueRef, _: Outcome) -> AdapterResult<()> {
            Ok(())
        }
        fn list_by_creator(&self, _: u64) -> AdapterResult<Vec<IssueSummary>> {
            Ok(vec![])
        }
        fn read(&self, _: &IssueRef) -> AdapterResult<IssueState> {
            Err(AdapterError::NotFound)
        }
        fn history_after(
            &self,
            _: &IssueRef,
            _: Option<&EventId>,
        ) -> AdapterResult<Vec<HistoryEntry>> {
            Ok(vec![])
        }
        fn add_labels(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            Ok(())
        }
        fn remove_labels(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            Ok(())
        }
        fn add_assignees(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            Ok(())
        }
        fn remove_assignees(&mut self, _: &IssueRef, _: &[String]) -> AdapterResult<()> {
            Ok(())
        }
        fn link(&mut self, _: &IssueRef, _: RelationKind, _: &IssueRef) -> AdapterResult<()> {
            Ok(())
        }
        fn inventory(&self) -> AdapterResult<Inventory> {
            if self.visible {
                Ok(Inventory::default())
            } else {
                Err(AdapterError::NotFound)
            }
        }
    }

    /// Host with scripted work; records calls and "mutates" by changing shards.
    struct Host {
        items: Vec<WorkItem>,
        universe: Vec<String>,
        changes: bool,
        bad: Option<String>,
        log: Vec<LedgerCommit>,
        cursor: Option<String>,
        calls: Vec<(WorkClass, String)>,
        after: usize,
        remaining: u64,
    }

    impl Host {
        fn new(items: Vec<WorkItem>, changes: bool) -> Self {
            Self {
                items,
                universe: vec![],
                changes,
                bad: None,
                log: vec![],
                cursor: None,
                calls: vec![],
                after: 0,
                remaining: 1000,
            }
        }
    }

    impl RunHost for Host {
        fn rate_limit(&self) -> RateLimit {
            RateLimit {
                remaining: Some(self.remaining),
                reset: Some(5),
            }
        }
        fn pending<S: ShardStore>(&self, _store: &S) -> Vec<WorkItem> {
            self.items.clone()
        }
        fn sweep_universe(&self) -> Vec<String> {
            self.universe.clone()
        }
        fn ledger_commits(&self) -> Vec<LedgerCommit> {
            self.log.clone()
        }
        fn feed_cursor(&self) -> Option<String> {
            self.cursor.clone()
        }
        fn execute<S: ShardStore>(
            &mut self,
            item: &WorkItem,
            _store: &mut S,
            _adapter: &mut dyn TrackerAdapter,
        ) -> Result<Option<Shard>, ItemError> {
            self.calls.push((item.class, item.ticket.clone()));
            if self.bad.as_deref() == Some(item.ticket.as_str()) {
                return Err(ItemError::Failed("cannot render".into()));
            }
            Ok(self.changes.then(|| Shard::new(&item.ticket)))
        }
        fn after_items(&mut self, _adapter: &mut dyn TrackerAdapter) {
            self.after += 1;
        }
    }

    fn cfg() -> RunConfig {
        RunConfig {
            run_id: "run-1".into(),
            now: 100,
            lock_ttl_secs: 3600,
            commit_every: 2,
            sweep_k: 1,
            bot_id: 9,
            budget: BudgetConfig {
                spacing: Duration::ZERO,
                ..BudgetConfig::default()
            },
        }
    }

    fn item(class: WorkClass, t: &str) -> WorkItem {
        WorkItem {
            class,
            age: 1,
            ticket: t.into(),
        }
    }

    fn ran(o: RunOutcome) -> RunSummary {
        match o {
            RunOutcome::Ran(s) => s,
            other => panic!("expected a run, got {other:?}"),
        }
    }

    // frob:tests run
    #[test]
    fn after_items_runs_once_per_completed_run() {
        let mut host = Host::new(vec![item(WorkClass::Update, "u")], true);
        ran(run(
            &mut Mem::default(),
            &mut Fake { visible: true },
            &mut host,
            &cfg(),
        )
        .unwrap());
        assert_eq!(host.after, 1);
    }

    // frob:tests run
    #[test]
    fn five_classes_execute_in_priority_order() {
        use WorkClass::{Create, Reconcile, Recovery, Sweep, Update};
        let items = vec![
            item(Reconcile, "r"),
            item(Create, "c"),
            item(Update, "u"),
            item(Recovery, "x"),
        ];
        let mut host = Host::new(items, true);
        host.universe = vec!["s".into()];
        let mut store = Mem::default();
        let out = run(&mut store, &mut Fake { visible: true }, &mut host, &cfg()).unwrap();
        let s = ran(out);
        let classes: Vec<_> = s.executed.iter().map(|(c, _)| *c).collect();
        assert_eq!(classes, [Recovery, Update, Create, Reconcile, Sweep]);
        assert_eq!(s.report.committed_ops, 5);
    }

    // frob:tests run
    #[test]
    fn feed_cursor_advances_only_after_a_clean_reconcile() {
        let cursor = Some("2026-10-05T00:00:00Z".to_string());
        let mut host = Host::new(vec![item(WorkClass::Reconcile, "r")], false);
        host.cursor.clone_from(&cursor);
        let mut store = Mem::default();
        run(&mut store, &mut Fake { visible: true }, &mut host, &cfg()).unwrap();
        let index = crate::progress::read_index(&store).unwrap();
        assert_eq!(index.change_feed, cursor);

        let mut held = Host::new(vec![item(WorkClass::Reconcile, "r")], false);
        held.cursor.clone_from(&cursor);
        held.bad = Some("r".into());
        let mut store = Mem::default();
        run(&mut store, &mut Fake { visible: true }, &mut held, &cfg()).unwrap();
        assert_eq!(
            crate::progress::read_index(&store).unwrap().change_feed,
            None
        );
    }

    // frob:tests run
    #[test]
    fn converged_state_changes_nothing() {
        let mut host = Host::new(vec![item(WorkClass::Update, "u")], false);
        let mut store = Mem::default();
        let s = ran(run(&mut store, &mut Fake { visible: true }, &mut host, &cfg()).unwrap());
        assert_eq!(s.report.committed_ops, 0);
        assert!(!store.puts.iter().any(|k| k == "index" || k == "u"));
    }

    // frob:tests run
    #[test]
    fn blind_run_stops_with_mir001_and_does_nothing() {
        let mut host = Host::new(vec![item(WorkClass::Update, "u")], true);
        let mut store = Mem::default();
        let out = run(&mut store, &mut Fake { visible: false }, &mut host, &cfg()).unwrap();
        match out {
            RunOutcome::Stopped { mir001 } => assert!(mir001.contains("MIR001 token-blind")),
            other => panic!("expected stop, got {other:?}"),
        }
        assert!(host.calls.is_empty());
        assert!(!store.puts.iter().any(|k| k == "index"));
    }

    // frob:tests run
    #[test]
    fn one_unrenderable_ticket_does_not_stop_the_others() {
        let items = vec![
            item(WorkClass::Update, "a"),
            item(WorkClass::Update, "b"),
            item(WorkClass::Update, "c"),
        ];
        let mut host = Host::new(items, true);
        host.bad = Some("b".into());
        let mut store = Mem::default();
        let s = ran(run(&mut store, &mut Fake { visible: true }, &mut host, &cfg()).unwrap());
        assert_eq!(s.failed, [("b".to_string(), "cannot render".to_string())]);
        let done: Vec<_> = s.executed.iter().map(|(_, t)| t.as_str()).collect();
        assert_eq!(done, ["a", "c"]);
    }

    // frob:tests run
    #[test]
    fn live_lock_means_busy_and_no_work() {
        let mut store = Mem::default();
        lock::acquire(&mut store, "other", 100, 3600).unwrap();
        let mut host = Host::new(vec![item(WorkClass::Update, "u")], true);
        let out = run(&mut store, &mut Fake { visible: true }, &mut host, &cfg()).unwrap();
        assert_eq!(
            out,
            RunOutcome::Busy {
                holder: "other".into()
            }
        );
        assert!(host.calls.is_empty());
    }

    fn commit(id: &str, own: bool) -> LedgerCommit {
        LedgerCommit { id: id.into(), own }
    }

    // frob:tests run
    // frob:tests advance_watermark
    #[test]
    fn clean_run_advances_watermark_and_skips_own_commits() {
        let mut store = Mem::default();
        lock::write_watermark(&mut store, "c1").unwrap();
        let mut host = Host::new(vec![], false);
        host.log = vec![commit("c1", false), commit("c2", true), commit("c3", false)];
        let s = ran(run(&mut store, &mut Fake { visible: true }, &mut host, &cfg()).unwrap());
        assert_eq!(s.new_commits, 1);
        assert_eq!(s.watermark.as_deref(), Some("c3"));
        assert_eq!(lock::read_watermark(&store).unwrap().unwrap().commit, "c3");
        let again = ran(run(&mut store, &mut Fake { visible: true }, &mut host, &cfg()).unwrap());
        assert_eq!(again.new_commits, 0);
        assert_eq!(again.watermark, None);
    }

    // frob:tests run
    // frob:tests advance_watermark
    #[test]
    fn failed_ticket_holds_the_watermark() {
        let mut store = Mem::default();
        let mut host = Host::new(vec![item(WorkClass::Update, "b")], true);
        host.bad = Some("b".into());
        host.log = vec![commit("c1", false)];
        let s = ran(run(&mut store, &mut Fake { visible: true }, &mut host, &cfg()).unwrap());
        assert_eq!(s.watermark, None);
        assert!(lock::read_watermark(&store).unwrap().is_none());
    }

    /// A host and config whose budget (all of `3 * n` calls) fits exactly `n` items of cost 3.
    fn tight(host: &mut Host, n: u64, sweep_k: usize) -> RunConfig {
        host.remaining = n * 3;
        let mut c = cfg();
        c.sweep_k = sweep_k;
        c.budget.share_percent = 100;
        c
    }

    fn served(host: &mut Host, store: &mut Mem, cfg: &RunConfig) -> Vec<String> {
        let before = host.calls.len();
        ran(run(store, &mut Fake { visible: true }, host, cfg).unwrap());
        host.calls[before..]
            .iter()
            .map(|(_, t)| t.clone())
            .collect()
    }

    // frob:tests run
    // frob:tests load_cursors
    // frob:tests save_cursors
    #[test]
    fn sweep_k_above_budget_capacity_visits_every_ticket() {
        let mut host = Host::new(vec![], false);
        host.universe = (0..7).map(|i| format!("S{i}")).collect();
        let mut store = Mem::default();
        let cfg = tight(&mut host, 3, 5);
        let mut seen = std::collections::BTreeSet::new();
        for _ in 0..3 {
            seen.extend(served(&mut host, &mut store, &cfg));
        }
        assert_eq!(seen.len(), 7, "a sweep ticket starved: {seen:?}");
    }

    // frob:tests run
    #[test]
    fn update_class_rotates_across_runs_under_a_small_budget() {
        let items = vec![
            item(WorkClass::Update, "a"),
            item(WorkClass::Update, "b"),
            item(WorkClass::Update, "c"),
        ];
        let mut host = Host::new(items, false);
        let mut store = Mem::default();
        let cfg = tight(&mut host, 1, 0);
        let order: Vec<String> = (0..4)
            .flat_map(|_| served(&mut host, &mut store, &cfg))
            .collect();
        assert_eq!(order, ["a", "b", "c", "a"]);
    }

    // frob:tests load_cursors
    // frob:tests save_cursors
    #[test]
    fn cursors_round_trip_and_old_store_means_fresh() {
        let mut store = Mem::default();
        assert_eq!(load_cursors(&store).unwrap(), Cursors::default());
        let mut c = Cursors::default();
        c.complete(&item(WorkClass::Create, "x"));
        c.complete(&item(WorkClass::Sweep, "y"));
        save_cursors(&mut store, &c).unwrap();
        assert_eq!(load_cursors(&store).unwrap(), c);
        store.data.insert(CURSORS_KEY.into(), b"{}".to_vec());
        assert_eq!(load_cursors(&store).unwrap(), Cursors::default());
        store.data.insert(CURSORS_KEY.into(), b"nope".to_vec());
        assert!(matches!(
            load_cursors(&store),
            Err(MapError::Corrupt { .. })
        ));
    }

    // frob:tests run
    #[test]
    fn cursor_past_removed_tickets_wraps_and_empty_run_writes_nothing() {
        let mut store = Mem::default();
        let mut host = Host::new(vec![item(WorkClass::Update, "z")], false);
        served(&mut host, &mut store, &cfg());
        // "z" is gone and the new work sorts before the stored cursor: it is still served.
        host.items = vec![item(WorkClass::Update, "a")];
        assert_eq!(served(&mut host, &mut store, &cfg()), ["a"]);
        let puts = store.puts.len();
        host.items.clear();
        served(&mut host, &mut store, &cfg());
        assert!(!store.puts[puts..].iter().any(|k| k == CURSORS_KEY));
    }
}
