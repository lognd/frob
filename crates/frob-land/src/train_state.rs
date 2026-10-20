//! Persistent state of the land train under `<common_dir>/frob/train` (frob:ticket 01M4Z1MYSTFADV8FJM8SEXKGZ7).
//!
//! Layout, every file replaced atomically:
//! - `state.json`: the one [`TrainRun`] in flight, written only by the driver,
//!   which holds `land.lock` for the whole train (no lock of its own here).
//! - `queue/<ULID>.json`: one [`QueueEntry`] per enqueued ticket, so enqueuers
//!   never rewrite each other's requests (as lease waiters do).
//! - `results/<ULID>.json`: one [`TicketResult`] per finished ticket, for the
//!   waiting enqueuer to read; [`TrainStore::prune_results`] bounds them.
//! - `batch.json`: the adaptive [`BatchSize`].
//!
//! Resume is git-derived: the run records oids and a [`Phase`], and
//! [`resume_phase`] corrects the stored phase with the one git fact that
//! matters (is the candidate already in the base). A run from a different
//! schema version is logged and discarded, never an error loop. A run whose
//! driver pid is dead is reported by [`TrainStore::status`] as stale and resumable.

use gob_path::Shown;
use std::path::{Path, PathBuf};

use frob_ledger::TicketId;
use gob_time::{Clock, SystemClock};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::error::LandError;
use crate::lock::pid_alive;
use crate::ratchet::FindingNote;

/// Version of the on-disk layouts; a run with another value is discarded on load.
pub const SCHEMA_VERSION: u32 = 1;

/// The driver process that owns a run: pid and start time.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct TrainOwner {
    /// Process id of the driver.
    pub pid: u32,
    /// Unix seconds when the driver started the run.
    pub started: i64,
}

impl TrainOwner {
    /// The calling process, started now.
    pub fn this_process() -> Self {
        Self {
            pid: std::process::id(),
            started: SystemClock.now().unix(),
        }
    }
}

/// Where a run stands; each phase is entered only after the previous one is durable.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Phase {
    /// Member branches are being merged into the candidate.
    Building,
    /// The candidate is being verified.
    Checking,
    /// The base advanced to the candidate; members are not all closed yet.
    Advanced,
    /// Members are being closed; a crash here resumes closing the rest.
    Closing,
    /// Everything is done.
    Done,
}

/// How one member ended, or that it has not yet.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum MemberStatus {
    /// In the candidate, not yet judged.
    Pending,
    /// Verified green in the candidate.
    Green,
    /// Identified as the culprit of a red candidate.
    Red,
    /// Evicted: conflict, or its branch moved since enqueue.
    Evicted,
    /// Closed as landed.
    Landed,
}

/// One ticket in a run, pinned to the head it was enqueued at.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct Member {
    /// The ticket (a ULID, stable where a handle is not).
    pub id: TicketId,
    /// Frozen head oid of its branch.
    pub head_oid: String,
    /// Where it stands.
    pub status: MemberStatus,
    /// Why it is red or evicted, when it is.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
}

/// The train in flight.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct TrainRun {
    /// Layout version, [`SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Run id (a ULID string), also the suffix of the candidate ref.
    pub id: String,
    /// Base commit the candidate was built on.
    pub base_oid: String,
    /// The combined commit, once built.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub candidate_oid: Option<String>,
    /// Members in landing order.
    pub members: Vec<Member>,
    /// Where the run stands.
    pub phase: Phase,
    /// Verification rounds done so far.
    pub rounds: u32,
    /// The driver process.
    pub owner: TrainOwner,
    /// Unix seconds of the last save.
    pub updated: i64,
}

impl TrainRun {
    /// A fresh run in [`Phase::Building`] owned by this process.
    pub fn new(id: impl Into<String>, base_oid: impl Into<String>, members: Vec<Member>) -> Self {
        Self {
            schema_version: SCHEMA_VERSION,
            id: id.into(),
            base_oid: base_oid.into(),
            candidate_oid: None,
            members,
            phase: Phase::Building,
            rounds: 0,
            owner: TrainOwner::this_process(),
            updated: 0,
        }
    }

    /// Check the invariants the JSON schema cannot express.
    ///
    /// # Errors
    ///
    /// A one-line reason naming the first violated invariant.
    pub fn validate(&self) -> Result<(), String> {
        if self.id.is_empty() || self.base_oid.is_empty() {
            return Err("run id and base_oid must be set".to_owned());
        }
        if let Some(dup) = self
            .members
            .iter()
            .enumerate()
            .find(|(i, m)| self.members[..*i].iter().any(|o| o.id == m.id))
        {
            return Err(format!("member {} listed twice", dup.1.id));
        }
        if let Some(m) = self.members.iter().find(|m| {
            matches!(m.status, MemberStatus::Red | MemberStatus::Evicted) && m.reason.is_none()
        }) {
            return Err(format!(
                "member {} is red or evicted without a reason",
                m.id
            ));
        }
        if matches!(
            self.phase,
            Phase::Checking | Phase::Advanced | Phase::Closing | Phase::Done
        ) && self.candidate_oid.is_none()
        {
            return Err(format!("phase {:?} needs a candidate_oid", self.phase));
        }
        Ok(())
    }
}

/// The phase to resume at: git's truth about the candidate wins over the stored phase.
///
/// `candidate_in_base` is whether `candidate_oid` is an ancestor of the base
/// (the advance happened even if the crash lost the `Advanced` save).
pub fn resume_phase(run: &TrainRun, candidate_in_base: bool) -> Phase {
    let resumed = match (run.phase, candidate_in_base, run.candidate_oid.is_some()) {
        (Phase::Done, _, _) => Phase::Done,
        (Phase::Advanced | Phase::Closing, _, _) => run.phase,
        (_, true, true) => Phase::Advanced,
        (Phase::Checking, false, true) => Phase::Checking,
        _ => Phase::Building,
    };
    tracing::info!(run = %run.id, stored = ?run.phase, resumed = ?resumed, candidate_in_base, "train resume phase");
    resumed
}

/// One enqueued ticket waiting for a train.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct QueueEntry {
    /// Layout version.
    pub schema_version: u32,
    /// The ticket.
    pub id: TicketId,
    /// Unix seconds when it was enqueued.
    pub enqueued_at: i64,
    /// Who enqueued it.
    pub actor: String,
    /// The worktree holding the branch.
    pub worktree: String,
    /// Frozen head oid of the branch at enqueue.
    pub head_oid: String,
    /// Raw blocking findings of the ticket-scoped rules run at enqueue for `head_oid`, outside the
    /// land lock; the driver re-ratchets them against the base instead of re-running (absent on
    /// entries written before this field existed, which the driver runs itself).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rules: Option<Vec<FindingNote>>,
}

/// What became of one ticket, for its enqueuer.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct TicketResult {
    /// Layout version.
    pub schema_version: u32,
    /// The ticket.
    pub id: TicketId,
    /// The run it was part of.
    pub run: String,
    /// Final status.
    pub status: MemberStatus,
    /// Why, for red or evicted.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
    /// Unix seconds when it finished.
    pub finished: i64,
}

/// The adaptive batch size: the controller grows and halves `current`, never above `max`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct BatchSize {
    /// The size the next run is built with.
    pub current: u32,
    /// The upper bound.
    pub max: u32,
}

impl Default for BatchSize {
    fn default() -> Self {
        Self { current: 1, max: 8 }
    }
}

impl BatchSize {
    /// Check `1 <= current <= max`.
    ///
    /// # Errors
    ///
    /// A one-line reason when the bounds are violated.
    pub fn validate(&self) -> Result<(), String> {
        if self.current == 0 || self.current > self.max {
            return Err(format!(
                "batch size {} is outside 1..={}",
                self.current, self.max
            ));
        }
        Ok(())
    }
}

/// What `status` found.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TrainStatus {
    /// The run in flight, when `state.json` exists.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub run: Option<TrainRun>,
    /// Tickets waiting in the queue.
    pub queued: usize,
    /// True when the run's driver is alive.
    pub live: bool,
    /// True when a run exists but its driver is gone.
    pub stale: bool,
    /// True when a new driver can pick the run up.
    pub resumable: bool,
    /// One-line human summary.
    pub summary: String,
}

/// The on-disk store of the train.
#[derive(Debug, Clone)]
pub struct TrainStore {
    dir: PathBuf,
}

impl TrainStore {
    /// The store below `common_dir` (`<common_dir>/frob/train`).
    pub fn new(common_dir: &Path) -> Self {
        Self {
            dir: common_dir.join("frob").join("train"),
        }
    }

    /// Path of the run document.
    pub fn state_path(&self) -> PathBuf {
        self.dir.join("state.json")
    }

    fn batch_path(&self) -> PathBuf {
        self.dir.join("batch.json")
    }

    fn queue_dir(&self) -> PathBuf {
        self.dir.join("queue")
    }

    fn results_dir(&self) -> PathBuf {
        self.dir.join("results")
    }

    /// Read the run in flight; `None` when there is none or its schema version is unknown (logged, discarded).
    ///
    /// # Errors
    ///
    /// `E-CONFIG` when the document is malformed or invalid; `E-LAND-IO` on read failure.
    pub fn load_run(&self) -> Result<Option<TrainRun>, LandError> {
        let path = self.state_path();
        let Some(value) = read_json::<serde_json::Value>(&path)? else {
            return Ok(None);
        };
        if value
            .get("schema_version")
            .and_then(serde_json::Value::as_u64)
            != Some(u64::from(SCHEMA_VERSION))
        {
            tracing::warn!(path = %Shown::of(&path), "train run has an unknown schema version; discarded");
            return Ok(None);
        }
        let run: TrainRun = serde_json::from_value(value)
            .map_err(|e| LandError::Config(format!("{}: {e}", Shown::of(&path))))?;
        run.validate()
            .map_err(|why| LandError::Config(format!("{}: {why}", Shown::of(&path))))?;
        Ok(Some(run))
    }

    /// Validate `run`, stamp `updated` and replace `state.json` atomically.
    ///
    /// # Errors
    ///
    /// `E-CONFIG` when `run` is invalid; `E-LAND-IO` when the write fails.
    pub fn save_run(&self, run: &mut TrainRun) -> Result<(), LandError> {
        run.validate()
            .map_err(|why| LandError::Config(format!("refusing to save train run: {why}")))?;
        run.updated = SystemClock.now().unix();
        write_json(&self.state_path(), run)?;
        tracing::debug!(run = %run.id, phase = ?run.phase, "train run saved");
        Ok(())
    }

    /// Remove the run document once the run is done.
    ///
    /// # Errors
    ///
    /// `E-LAND-IO` when the file cannot be removed.
    pub fn clear_run(&self) -> Result<(), LandError> {
        remove_file(&self.state_path())
    }

    /// Enqueue a ticket (replacing its earlier entry).
    ///
    /// # Errors
    ///
    /// `E-LAND-IO` when the write fails.
    pub fn enqueue(&self, entry: &QueueEntry) -> Result<(), LandError> {
        write_json(&self.queue_dir().join(format!("{}.json", entry.id)), entry)?;
        tracing::info!(ticket = %entry.id, head = %entry.head_oid, "ticket enqueued for the train");
        Ok(())
    }

    /// Remove a ticket's queue entry.
    ///
    /// # Errors
    ///
    /// `E-LAND-IO` when the file cannot be removed.
    pub fn dequeue(&self, id: &TicketId) -> Result<(), LandError> {
        remove_file(&self.queue_dir().join(format!("{id}.json")))
    }

    /// The queue, oldest first (ties by id); unreadable entries are logged and skipped.
    ///
    /// # Errors
    ///
    /// `E-LAND-IO` when the directory cannot be listed.
    pub fn queue(&self) -> Result<Vec<QueueEntry>, LandError> {
        let mut entries: Vec<QueueEntry> = read_dir_json(&self.queue_dir())?;
        entries.sort_by_key(|e| (e.enqueued_at, e.id));
        Ok(entries)
    }

    /// Record a ticket's result.
    ///
    /// # Errors
    ///
    /// `E-LAND-IO` when the write fails.
    pub fn put_result(&self, result: &TicketResult) -> Result<(), LandError> {
        write_json(
            &self.results_dir().join(format!("{}.json", result.id)),
            result,
        )?;
        tracing::info!(ticket = %result.id, status = ?result.status, "train result recorded");
        Ok(())
    }

    /// A ticket's result, when one was recorded.
    ///
    /// # Errors
    ///
    /// `E-CONFIG` when malformed; `E-LAND-IO` on read failure.
    pub fn result(&self, id: &TicketId) -> Result<Option<TicketResult>, LandError> {
        read_json(&self.results_dir().join(format!("{id}.json")))
    }

    // frob:ticket 01M4Z1ND9ZM2NPAFJBF67JHDV6
    /// Forget a ticket's result, so a re-enqueued ticket never reads its previous run's verdict.
    ///
    /// # Errors
    ///
    /// `E-LAND-IO` when the file cannot be removed.
    pub fn clear_result(&self, id: &TicketId) -> Result<(), LandError> {
        remove_file(&self.results_dir().join(format!("{id}.json")))
    }

    /// Keep only the `keep` most recently finished results; returns how many were removed.
    ///
    /// # Errors
    ///
    /// `E-LAND-IO` when listing or removal fails.
    pub fn prune_results(&self, keep: usize) -> Result<usize, LandError> {
        let mut all: Vec<TicketResult> = read_dir_json(&self.results_dir())?;
        all.sort_by_key(|r| std::cmp::Reverse((r.finished, r.id)));
        let stale = all.split_off(keep.min(all.len()));
        for r in &stale {
            remove_file(&self.results_dir().join(format!("{}.json", r.id)))?;
        }
        if !stale.is_empty() {
            tracing::info!(removed = stale.len(), keep, "train results pruned");
        }
        Ok(stale.len())
    }

    /// The batch size; the default when none was stored.
    ///
    /// # Errors
    ///
    /// `E-CONFIG` when malformed or out of bounds; `E-LAND-IO` on read failure.
    pub fn batch(&self) -> Result<BatchSize, LandError> {
        let path = self.batch_path();
        let Some(batch) = read_json::<BatchSize>(&path)? else {
            return Ok(BatchSize::default());
        };
        batch
            .validate()
            .map_err(|why| LandError::Config(format!("{}: {why}", Shown::of(&path))))?;
        Ok(batch)
    }

    /// Validate and store the batch size.
    ///
    /// # Errors
    ///
    /// `E-CONFIG` when out of bounds; `E-LAND-IO` when the write fails.
    pub fn set_batch(&self, batch: &BatchSize) -> Result<(), LandError> {
        batch
            .validate()
            .map_err(|why| LandError::Config(format!("refusing to save batch size: {why}")))?;
        write_json(&self.batch_path(), batch)
    }

    /// Report the train: live, stale and resumable, without taking anything over.
    ///
    /// # Errors
    ///
    /// As [`TrainStore::load_run`] and [`TrainStore::queue`].
    pub fn status(&self) -> Result<TrainStatus, LandError> {
        let run = self.load_run()?;
        let queued = self.queue()?.len();
        let live = run.as_ref().is_some_and(|r| pid_alive(r.owner.pid));
        let stale = run.as_ref().is_some_and(|r| r.phase != Phase::Done) && !live;
        let summary = match (&run, live, stale) {
            (None, _, _) => format!("no train in flight, {queued} queued"),
            (Some(r), true, _) => format!(
                "train {} {:?}: {} members, {queued} queued",
                r.id,
                r.phase,
                r.members.len()
            ),
            (Some(r), false, true) => format!(
                "stale train {} ({:?}): driver pid {} is gone; resumable, {queued} queued",
                r.id, r.phase, r.owner.pid
            ),
            (Some(r), false, false) => format!("train {} finished, {queued} queued", r.id),
        };
        if stale {
            tracing::warn!(%summary, "dead train driver recovered as stale");
        }
        Ok(TrainStatus {
            run,
            queued,
            live,
            stale,
            resumable: stale,
            summary,
        })
    }
}

/// The JSON Schema of [`TrainRun`].
pub fn run_schema() -> schemars::Schema {
    schemars::schema_for!(TrainRun)
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<(), LandError> {
    let text = serde_json::to_string_pretty(value)
        .map_err(|e| LandError::Config(format!("encoding {}: {e}", Shown::of(path))))?;
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir)
            .map_err(|e| LandError::io(format!("creating {}", Shown::of(dir)), e))?;
    }
    gob_fs::write_atomic(path, format!("{text}\n").as_bytes())
        .map_err(|e| LandError::io(format!("writing {}", Shown::of(path)), e))
}

fn read_json<T: serde::de::DeserializeOwned>(path: &Path) -> Result<Option<T>, LandError> {
    let text = match std::fs::read_to_string(path) {
        Ok(t) => t,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(LandError::io(format!("reading {}", Shown::of(path)), e)),
    };
    serde_json::from_str(&text)
        .map(Some)
        .map_err(|e| LandError::Config(format!("{}: {e}", Shown::of(path))))
}

fn read_dir_json<T: serde::de::DeserializeOwned>(dir: &Path) -> Result<Vec<T>, LandError> {
    let read = match std::fs::read_dir(dir) {
        Ok(r) => r,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
        Err(e) => return Err(LandError::io(format!("listing {}", Shown::of(dir)), e)),
    };
    let mut out = Vec::new();
    for entry in read {
        let path = entry
            .map_err(|e| LandError::io(format!("listing {}", Shown::of(dir)), e))?
            .path();
        if path.extension().is_none_or(|x| x != "json") {
            continue;
        }
        match read_json::<T>(&path) {
            Ok(Some(v)) => out.push(v),
            Ok(None) => {}
            Err(e) => {
                tracing::warn!(path = %Shown::of(&path), error = %e, "unreadable train file skipped");
            }
        }
    }
    Ok(out)
}

fn remove_file(path: &Path) -> Result<(), LandError> {
    match std::fs::remove_file(path) {
        Ok(()) => Ok(()),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(e) => Err(LandError::io(format!("removing {}", Shown::of(path)), e)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn member(status: MemberStatus) -> Member {
        Member {
            id: TicketId::mint(),
            head_oid: "a".repeat(40),
            status,
            reason: None,
        }
    }

    fn run() -> TrainRun {
        TrainRun::new(
            "RUN1",
            "b".repeat(40),
            vec![member(MemberStatus::Pending), member(MemberStatus::Green)],
        )
    }

    // frob:tests crates/frob-land/src/train_state.rs::TrainStore.save_run
    #[test]
    fn written_run_round_trips_and_matches_schema() {
        let dir = tempfile::tempdir().unwrap();
        let store = TrainStore::new(dir.path());
        assert!(store.load_run().unwrap().is_none());
        let mut r = run();
        r.candidate_oid = Some("c".repeat(40));
        r.phase = Phase::Checking;
        store.save_run(&mut r).unwrap();
        assert_eq!(store.load_run().unwrap().unwrap(), r);
        let schema = serde_json::to_value(run_schema()).unwrap();
        let props = schema["properties"].as_object().unwrap();
        let doc: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(store.state_path()).unwrap()).unwrap();
        for key in doc.as_object().unwrap().keys() {
            assert!(props.contains_key(key), "{key} missing from schema");
        }
        for req in schema["required"].as_array().unwrap() {
            assert!(doc.get(req.as_str().unwrap()).is_some());
        }
    }

    // frob:tests crates/frob-land/src/train_state.rs::TrainRun.validate
    #[test]
    fn invalid_run_is_refused_and_unknown_schema_discarded() {
        let dir = tempfile::tempdir().unwrap();
        let store = TrainStore::new(dir.path());
        let mut no_cand = run();
        no_cand.phase = Phase::Checking;
        assert!(store.save_run(&mut no_cand).is_err());
        let mut red = run();
        red.members[0].status = MemberStatus::Red;
        assert!(red.validate().is_err());
        let mut dup = run();
        dup.members.push(dup.members[0].clone());
        assert!(dup.validate().is_err());
        std::fs::create_dir_all(dir.path().join("frob/train")).unwrap();
        std::fs::write(store.state_path(), r#"{"schema_version": 99}"#).unwrap();
        assert!(store.load_run().unwrap().is_none());
        std::fs::write(store.state_path(), "{not json").unwrap();
        assert!(store.load_run().is_err());
    }

    // frob:tests crates/frob-land/src/train_state.rs::TrainStore.status
    #[cfg(target_os = "linux")]
    #[test]
    fn crashed_driver_is_reported_stale_and_resumable() {
        let dir = tempfile::tempdir().unwrap();
        let store = TrainStore::new(dir.path());
        let mut live = run();
        store.save_run(&mut live).unwrap();
        let s = store.status().unwrap();
        assert!(s.live && !s.stale && !s.resumable);
        let mut dead = run();
        dead.owner = TrainOwner {
            pid: u32::MAX - 1,
            started: 1,
        };
        store.save_run(&mut dead).unwrap();
        let s = store.status().unwrap();
        assert!(s.stale && s.resumable && !s.live);
        assert!(s.summary.contains("stale"));
        store.clear_run().unwrap();
        assert!(!store.status().unwrap().stale);
    }

    // frob:tests crates/frob-land/src/train_state.rs::resume_phase
    #[test]
    fn resume_trusts_git_over_the_stored_phase() {
        let mut r = run();
        r.candidate_oid = Some("c".repeat(40));
        r.phase = Phase::Checking;
        assert_eq!(resume_phase(&r, true), Phase::Advanced);
        assert_eq!(resume_phase(&r, false), Phase::Checking);
        r.phase = Phase::Closing;
        assert_eq!(resume_phase(&r, true), Phase::Closing);
        r.phase = Phase::Building;
        r.candidate_oid = None;
        assert_eq!(resume_phase(&r, false), Phase::Building);
    }

    // frob:tests crates/frob-land/src/train_state.rs::TrainStore.enqueue
    #[test]
    fn queue_entries_are_independent_files_and_results_prune() {
        let dir = tempfile::tempdir().unwrap();
        let store = TrainStore::new(dir.path());
        let mk = |t| QueueEntry {
            schema_version: SCHEMA_VERSION,
            id: TicketId::mint(),
            enqueued_at: t,
            actor: "a".into(),
            worktree: "/w".into(),
            head_oid: "d".repeat(40),
            rules: None,
        };
        let (b, a) = (mk(20), mk(10));
        store.enqueue(&b).unwrap();
        store.enqueue(&a).unwrap();
        let q = store.queue().unwrap();
        assert_eq!(q.iter().map(|e| e.id).collect::<Vec<_>>(), vec![a.id, b.id]);
        store.dequeue(&a.id).unwrap();
        assert_eq!(store.queue().unwrap().len(), 1);
        for t in 0..4 {
            store
                .put_result(&TicketResult {
                    schema_version: SCHEMA_VERSION,
                    id: TicketId::mint(),
                    run: "RUN1".into(),
                    status: MemberStatus::Landed,
                    reason: None,
                    finished: t,
                })
                .unwrap();
        }
        assert_eq!(store.prune_results(2).unwrap(), 2);
        assert!(store.result(&b.id).unwrap().is_none());
    }

    // frob:tests crates/frob-land/src/train_state.rs::TrainStore.set_batch
    #[test]
    fn batch_size_is_bounded_and_defaults() {
        let dir = tempfile::tempdir().unwrap();
        let store = TrainStore::new(dir.path());
        assert_eq!(store.batch().unwrap(), BatchSize::default());
        store.set_batch(&BatchSize { current: 4, max: 6 }).unwrap();
        assert_eq!(store.batch().unwrap().current, 4);
        assert!(store.set_batch(&BatchSize { current: 0, max: 6 }).is_err());
        assert!(store.set_batch(&BatchSize { current: 7, max: 6 }).is_err());
    }
}
