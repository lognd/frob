//! The mirror run driver (mirror.md 3.1 to 3.4): lock, blindness, budget, work classes in strict
//! priority with the feed and the sweep, per-ticket isolation, progress commits and a report.
//!
//! The driver owns ordering and bookkeeping only; what one work item does to the tracker is the
//! host's `execute`, so a run over a converged state asks for no work and commits nothing.

// frob:ticket 01M4052W6Q1FAQK362YF6RCGW1

use tracing::{debug, info, warn};

use crate::adapter::TrackerAdapter;
use crate::blind::check_blind;
use crate::budget::{self, BudgetConfig, RateLimit};
use crate::lock::{self, Acquire, LedgerCommit};
use crate::mapfile::{MapError, Shard, ShardStore};
use crate::plan::{Cursors, WorkClass, WorkItem, select};
use crate::progress::{ProgressWriter, RunReport, StopReason};
use crate::sweep::next_batch;

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
    fn pending(&self) -> Vec<WorkItem>;
    /// Every mirrored ticket ULID, the sweep's universe.
    fn sweep_universe(&self) -> Vec<String>;
    /// The ledger commit log, oldest first, own commits flagged; empty when the host has none.
    fn ledger_commits(&self) -> Vec<LedgerCommit> {
        Vec::new()
    }
    /// Does one item; `Ok(None)` means nothing changed, `Ok(Some)` returns the shard to commit.
    ///
    /// # Errors
    /// `ItemError::RateLimited` stops the run; `ItemError::Failed` skips this ticket only.
    fn execute(&mut self, item: &WorkItem) -> Result<Option<Shard>, ItemError>;
    /// Per-run housekeeping after the items ran and before the final commit (for example
    /// closing duplicate issues); a failure is the host's to log and never fails the run.
    fn after_items(&mut self) {}
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
    adapter: &dyn TrackerAdapter,
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
    adapter: &dyn TrackerAdapter,
    host: &mut H,
    cfg: &RunConfig,
) -> Result<RunOutcome, MapError> {
    if let Err(e) = check_blind(adapter, cfg.bot_id) {
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
    let mut writer = ProgressWriter::new(store, cfg.commit_every)?;
    let mut items = host.pending();
    let universe = host.sweep_universe();
    items.extend(
        next_batch(&universe, writer.resume_after(), cfg.sweep_k)
            .into_iter()
            .map(|ticket| WorkItem {
                class: WorkClass::Sweep,
                age: 0,
                ticket,
            }),
    );
    let cost = cfg.budget.reads_per_ticket + 1;
    let selected = select(items, &Cursors::default(), &plan, cost);
    debug!(selected = selected.len(), "mirror run: work selected");
    let (mut cursors, mut executed, mut failed) = (Cursors::default(), Vec::new(), Vec::new());
    let mut stop = StopReason::Completed;
    for item in &selected {
        match host.execute(item) {
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
        host.after_items();
    }
    let report = writer.finish(stop)?;
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
        calls: Vec<(WorkClass, String)>,
        after: usize,
    }

    impl Host {
        fn new(items: Vec<WorkItem>, changes: bool) -> Self {
            Self {
                items,
                universe: vec![],
                changes,
                bad: None,
                log: vec![],
                calls: vec![],
                after: 0,
            }
        }
    }

    impl RunHost for Host {
        fn rate_limit(&self) -> RateLimit {
            RateLimit {
                remaining: Some(1000),
                reset: Some(5),
            }
        }
        fn pending(&self) -> Vec<WorkItem> {
            self.items.clone()
        }
        fn sweep_universe(&self) -> Vec<String> {
            self.universe.clone()
        }
        fn ledger_commits(&self) -> Vec<LedgerCommit> {
            self.log.clone()
        }
        fn execute(&mut self, item: &WorkItem) -> Result<Option<Shard>, ItemError> {
            self.calls.push((item.class, item.ticket.clone()));
            if self.bad.as_deref() == Some(item.ticket.as_str()) {
                return Err(ItemError::Failed("cannot render".into()));
            }
            Ok(self.changes.then(|| Shard::new(&item.ticket)))
        }
        fn after_items(&mut self) {
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
            &Fake { visible: true },
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
        let out = run(&mut store, &Fake { visible: true }, &mut host, &cfg()).unwrap();
        let s = ran(out);
        let classes: Vec<_> = s.executed.iter().map(|(c, _)| *c).collect();
        assert_eq!(classes, [Recovery, Update, Create, Reconcile, Sweep]);
        assert_eq!(s.report.committed_ops, 5);
    }

    // frob:tests run
    #[test]
    fn converged_state_changes_nothing() {
        let mut host = Host::new(vec![item(WorkClass::Update, "u")], false);
        let mut store = Mem::default();
        let s = ran(run(&mut store, &Fake { visible: true }, &mut host, &cfg()).unwrap());
        assert_eq!(s.report.committed_ops, 0);
        assert!(!store.puts.iter().any(|k| k == "index" || k == "u"));
    }

    // frob:tests run
    #[test]
    fn blind_run_stops_with_mir001_and_does_nothing() {
        let mut host = Host::new(vec![item(WorkClass::Update, "u")], true);
        let mut store = Mem::default();
        let out = run(&mut store, &Fake { visible: false }, &mut host, &cfg()).unwrap();
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
        let s = ran(run(&mut store, &Fake { visible: true }, &mut host, &cfg()).unwrap());
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
        let out = run(&mut store, &Fake { visible: true }, &mut host, &cfg()).unwrap();
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
        let s = ran(run(&mut store, &Fake { visible: true }, &mut host, &cfg()).unwrap());
        assert_eq!(s.new_commits, 1);
        assert_eq!(s.watermark.as_deref(), Some("c3"));
        assert_eq!(lock::read_watermark(&store).unwrap().unwrap().commit, "c3");
        let again = ran(run(&mut store, &Fake { visible: true }, &mut host, &cfg()).unwrap());
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
        let s = ran(run(&mut store, &Fake { visible: true }, &mut host, &cfg()).unwrap());
        assert_eq!(s.watermark, None);
        assert!(lock::read_watermark(&store).unwrap().is_none());
    }
}
