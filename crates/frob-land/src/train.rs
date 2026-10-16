//! The land train driver (frob:ticket 01M4Z1ND9ZM2NPAFJBF67JHDV6, replaces the prefix bisection of 01M4MH62H1AE14Z472QDSD1QBK).
//!
//! Ready tickets are enqueued ([`enqueue`]); whoever holds the land lock drives the train
//! (`Driver::drain`): it takes the oldest ready tickets up to the adaptive batch size, skips any
//! whose scope overlaps one already chosen, finds the landable subset with the bisection planner
//! over sequential candidate checks, builds the final candidate, closes it with
//! [`TrainCloser::close_run`] and cleans up each landed member. A culprit gets a red result with the
//! failing evidence and keeps its lease and worktree so its agent can fix and enqueue again. The
//! batch size grows after a green round and halves after a red one. `land --train` ([`land_train`])
//! is the enqueuer (`--enqueue-only` queues the ticket and returns at once; a queued ticket's lease is
//! flagged so it leaves the WIP count, and a red or evicted result is written to the ticket as a
//! comment and a label): it waits for its own result, driving the train itself when nobody else does, and
//! falls back to the plain single-ticket [`land`] for a lone ticket or when `[land] train` is off.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use frob_evidence::Workspace;
use frob_ledger::TicketId;
use frob_ledger::model::CommentSubtype;
use frob_ledger::ops::Patch;
use gob_git::{Repo, TreeRef};
use gob_time::Clock;
use schemars::JsonSchema;
use serde::Serialize;

use crate::base_ci::{CachedCi, LandConfig, read_config};
use crate::batch_size::{self, Outcome as SizeOutcome};
use crate::bisect::{self, CheckFault, Plan, Runner, Verdict};
use crate::candidate::{CandidateMember, build_candidate, scopes_overlap};
use crate::error::{LandError, needs_action};
use crate::land::{
    Begun, Preconditions, already_done, base_ref, begin, blank_outcome, finish_member, land,
    preconditions, primary_root,
};
use crate::lock::{CODE_LOCKED, LandLock};
use crate::plan::{LandOptions, LandOutcome};
use crate::ratchet::{self, FindingNote};
use crate::train_check::{CandidateChecker, GitBackend, MemberInfo, run_member_rules};
use crate::train_close::{CloseMember, TrainCloser};
use crate::train_state::{
    BatchSize, Member, MemberStatus, Phase, QueueEntry, SCHEMA_VERSION, TicketResult, TrainRun,
    TrainStore, resume_phase,
};

/// Finished results kept for waiting enqueuers.
const KEEP_RESULTS: usize = 256;

/// Label a ticket carries after the train found it red, until it is enqueued again.
pub const TRAIN_RED: &str = "train-red";

/// Label a ticket carries after the train evicted it, until it is enqueued again.
pub const TRAIN_EVICTED: &str = "train-evicted";

/// The other train result label (the one to drop when `label` is set).
fn other_label(label: &str) -> &'static str {
    if label == TRAIN_RED {
        TRAIN_EVICTED
    } else {
        TRAIN_RED
    }
}

/// Set or clear the queued flag on a ticket's lease, whoever holds it; failures only warn.
fn mark_queued(root: &Path, clock: &Arc<dyn Clock>, id: TicketId, queued: bool) {
    let result = frob_lease::open_store_from_file(root, clock.clone())
        .map_err(|e| e.to_string())
        .and_then(|(leases, _)| {
            let held = leases.recorded_lease(id).map_err(|e| e.to_string())?;
            let Some(lease) = held else {
                return Ok(());
            };
            leases
                .set_queued(id, &lease.holder, queued)
                .map(|_| ())
                .map_err(|e| e.to_string())
        });
    if let Err(e) = result {
        tracing::warn!(ticket = %id, queued, error = %e, "lease queued flag not updated");
    }
}

/// Drop the train result labels from a ticket that is being enqueued again; failures only warn.
fn clear_result_labels(ledger: &frob_ledger::Ledger, id: TicketId) {
    let patch = Patch {
        remove_labels: vec![TRAIN_RED.to_owned(), TRAIN_EVICTED.to_owned()],
        ..Patch::default()
    };
    if let Err(e) = ledger.update(id, &patch) {
        tracing::warn!(ticket = %id, error = %e, "train labels not cleared");
    }
}

/// How long a waiting enqueuer sleeps between lock attempts.
const POLL: Duration = Duration::from_millis(200);

/// Options of the train verbs.
#[derive(Clone)]
pub struct TrainOptions {
    /// Options each member lands with (wait, outcome, base-CI override, ...).
    pub land: LandOptions,
    /// Checks batches instead of the real candidate checker; the seam tests inject a failing member through.
    pub runner: Option<Arc<dyn Runner>>,
    /// Queue the ticket and return without driving or waiting (`land --enqueue-only`).
    pub enqueue_only: bool,
}

impl std::fmt::Debug for TrainOptions {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("TrainOptions")
            .field("land", &self.land)
            .field("runner", &self.runner.as_ref().map(|_| "<injected>"))
            .field("enqueue_only", &self.enqueue_only)
            .finish()
    }
}

impl TrainOptions {
    /// Options for a verb: the real checker with `land`'s settings.
    pub fn new(land: LandOptions) -> Self {
        Self {
            land,
            runner: None,
            enqueue_only: false,
        }
    }
}

/// One culprit a round isolated.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CulpritReport {
    /// The ticket handle.
    pub handle: String,
    /// The failing evidence; the ticket goes back to its agent with it.
    pub evidence: String,
}

/// What one train round did.
#[derive(Debug, Clone, Default, Serialize, JsonSchema)]
pub struct RoundReport {
    /// The run id of the round.
    pub run: String,
    /// Tickets taken into the batch.
    pub considered: Vec<String>,
    /// Tickets landed, in order.
    pub landed: Vec<String>,
    /// Tickets isolated as the reason the batch was red.
    pub culprits: Vec<CulpritReport>,
    /// Tickets dropped from the queue (gone worktree, moved branch, already done) with why.
    pub evicted: Vec<String>,
    /// Tickets left queued because their scope overlaps a chosen ticket.
    pub skipped: Vec<String>,
    /// Candidate checks the round ran.
    pub checks: u32,
    /// The batch size the round used.
    pub batch_size: u32,
    /// Non-fatal notices.
    pub warnings: Vec<String>,
}

impl RoundReport {
    /// True when the round changed the queue (so another round may make progress).
    fn progressed(&self) -> bool {
        !(self.landed.is_empty() && self.culprits.is_empty() && self.evicted.is_empty())
    }
}

/// What `frob train run` and `frob train drain` did.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TrainRunReport {
    /// The rounds that ran, in order.
    pub rounds: Vec<RoundReport>,
    /// Tickets still queued afterwards.
    pub remaining: usize,
}

/// What `frob train status` found.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TrainStatusReport {
    /// One-line human summary.
    pub summary: String,
    /// True when `[land] train` is on for the base branch.
    pub enabled: bool,
    /// The queue, oldest first.
    pub queue: Vec<QueueEntry>,
    /// The run in flight or left behind, with its candidate, phase and members.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub current: Option<TrainRun>,
    /// The adaptive batch size and its cap.
    pub batch: BatchSize,
    /// True when the run's driver is alive.
    pub live: bool,
    /// True when a run exists whose driver is gone.
    pub stale: bool,
}

/// The repository facts every train operation needs, resolved from any checkout.
struct Site {
    repo: Repo,
    primary: PathBuf,
    ws: Workspace,
    base: String,
    cfg: LandConfig,
    store: TrainStore,
}

impl Site {
    /// Open the primary checkout of the repository containing `root`.
    fn open(root: &Path, clock: &Arc<dyn Clock>) -> Result<Self, LandError> {
        let found = Repo::discover(root).map_err(|e| LandError::Config(e.to_string()))?;
        let primary = primary_root(&found)?;
        let repo = Repo::discover(&primary).map_err(|e| LandError::Config(e.to_string()))?;
        let ws = Workspace::open(&primary, clock.clone())?;
        let base = frob_worktree::work::base_branch(&ws.ledger);
        let cfg = read_config(&repo, &base)?;
        let store = TrainStore::new(repo.common_dir());
        Ok(Self {
            repo,
            primary,
            ws,
            base,
            cfg,
            store,
        })
    }
}

/// The planner's runner over a borrowed trait object (the planner needs a sized runner).
struct DynRunner<'a>(&'a dyn Runner);

impl Runner for DynRunner<'_> {
    fn check(&self, subset: &[String]) -> Result<Verdict, CheckFault> {
        self.0.check(subset)
    }
}

/// A queued ticket loaded for a round: its preconditions and what the checker needs.
struct Chosen {
    entry: QueueEntry,
    pre: Preconditions,
    scope: Vec<String>,
    paths: Vec<String>,
}

/// Why a queued ticket could not join a round.
enum Unfit {
    /// The ticket is already closed.
    Closed,
    /// The ticket cannot land as enqueued; it leaves the queue with this reason.
    Evict(String),
}

/// Refusal codes that say the base, not the ticket, is the problem: they abort the round.
fn is_base_problem(e: &LandError) -> bool {
    e.refusal()
        .is_some_and(|r| r.code == "E-LAND-BASE-RED" || r.code == "E-LAND-BASE-CI-UNKNOWN")
}

/// True for the lock-is-busy refusal.
fn is_locked(e: &LandError) -> bool {
    e.refusal().is_some_and(|r| r.code == CODE_LOCKED)
}

/// The driver of the train; holds the land lock for as long as it lives.
struct Driver<'a> {
    site: Site,
    opts: &'a TrainOptions,
    clock: &'a Arc<dyn Clock>,
    lock: LandLock,
    seq: u32,
    /// Red and evicted results waiting to be written onto their tickets once the round has published
    /// (a ledger write mid-round would move a base branch that also carries the ledger).
    handbacks: Mutex<Vec<(TicketId, MemberStatus, Option<String>)>>,
    /// Base CI read once per round and shared by every member's preconditions.
    ci: Arc<CachedCi>,
}

impl<'a> Driver<'a> {
    /// Take the land lock (waiting up to `wait`) and open the repository for driving.
    fn start(
        root: &Path,
        opts: &'a TrainOptions,
        clock: &'a Arc<dyn Clock>,
        wait: Duration,
    ) -> Result<Self, LandError> {
        let site = Site::open(root, clock)?;
        let actor = site.ws.ledger.actor()?;
        let lock = LandLock::acquire(
            site.repo.common_dir(),
            wait,
            &format!("{actor} driving the land train"),
        )?;
        tracing::info!(base = %site.base, "train driver started");
        Ok(Self {
            site,
            opts,
            clock,
            lock,
            seq: 0,
            handbacks: Mutex::new(Vec::new()),
            ci: Arc::new(CachedCi::new(opts.land.ci_reader.clone())),
        })
    }

    /// Load one queued ticket for a round.
    fn load(&self, entry: &QueueEntry) -> Result<Result<Chosen, Unfit>, LandError> {
        let lo = LandOptions {
            handle: Some(entry.id.to_string()),
            dry_run: false,
            ci_reader: Some(self.ci.clone()),
            ..self.opts.land.clone()
        };
        let begun = match begin(Path::new(&entry.worktree), &lo, self.clock) {
            Ok(b) => b,
            Err(e @ (LandError::Config(_) | LandError::Io { .. } | LandError::Refused(_))) => {
                return Ok(Err(Unfit::Evict(format!(
                    "its worktree {} is unusable: {e}",
                    entry.worktree
                ))));
            }
            Err(e) => return Err(e),
        };
        if begun.view.summary.category == frob_ledger::model::Category::Done {
            return Ok(Err(Unfit::Closed));
        }
        let Begun {
            repo,
            cwd_root,
            here,
            leases,
            view,
            base,
            id,
            ..
        } = begun;
        let pre = match preconditions(repo, &cwd_root, here, &leases, &view, &base, &lo) {
            Ok(p) => p,
            Err(e) if is_base_problem(&e) => return Err(e),
            Err(e @ (LandError::Refused(_) | LandError::Config(_))) => {
                return Ok(Err(Unfit::Evict(e.to_string())));
            }
            Err(e) => return Err(e),
        };
        let scope = Self::renewed_scope(&leases, id)?;
        let Some(scope) = scope else {
            return Ok(Err(Unfit::Evict(
                "its lease is gone and could not be renewed; run `frob work` and enqueue again"
                    .to_owned(),
            )));
        };
        let head = pre.wt.rev_parse(&pre.branch)?;
        let head_text = head.to_string();
        if head_text != entry.head_oid {
            return Ok(Err(Unfit::Evict(format!(
                "its branch moved since it was enqueued ({} -> {head}); run `frob land --train` again",
                entry.head_oid
            ))));
        }
        let paths = pre
            .wt
            .diff_names(&TreeRef::Oid(pre.base_oid), &TreeRef::Oid(head))?
            .into_iter()
            .map(|c| c.path)
            .collect();
        Ok(Ok(Chosen {
            entry: entry.clone(),
            pre,
            scope,
            paths,
        }))
    }

    /// Renew the member's lease for this round and return its scope; `None` when no lease exists.
    ///
    /// `preconditions` already re-took an expired lease, so a missing lease here is a real loss and
    /// must never be read as an empty scope (an empty scope overlaps nothing).
    fn renewed_scope(
        leases: &frob_lease::LeaseStore,
        id: TicketId,
    ) -> Result<Option<Vec<String>>, LandError> {
        let Some(lease) = leases.live_lease(id)? else {
            tracing::warn!(ticket = %id, "train: member has no live lease");
            return Ok(None);
        };
        let renewed = leases.renew(id, &lease.holder)?;
        tracing::debug!(ticket = %id, "train: member lease renewed for the round");
        Ok(Some(renewed.scope))
    }

    /// Record a ticket's end state for its waiting enqueuer and take it off the queue.
    fn settle(
        &self,
        id: &TicketId,
        run: &str,
        status: MemberStatus,
        reason: Option<String>,
    ) -> Result<(), LandError> {
        self.site.store.put_result(&TicketResult {
            schema_version: SCHEMA_VERSION,
            id: *id,
            run: run.to_owned(),
            status,
            reason: reason.clone(),
            finished: self.clock.now().unix(),
        })?;
        if matches!(status, MemberStatus::Red | MemberStatus::Evicted) {
            mark_queued(&self.site.primary, self.clock, *id, false);
            self.handbacks
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .push((*id, status, reason));
        }
        self.site.store.dequeue(id)
    }

    /// Write every pending red or evicted result onto its ticket (failures only warn).
    fn flush_handbacks(&self) {
        let pending = std::mem::take(
            &mut *self
                .handbacks
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner),
        );
        for (id, status, reason) in pending {
            self.record_on_ticket(&id, status, reason.as_deref());
        }
    }

    /// Write one red or evicted result onto its ticket as a comment and a label (failures only warn).
    fn record_on_ticket(&self, id: &TicketId, status: MemberStatus, reason: Option<&str>) {
        let (label, verdict) = if status == MemberStatus::Red {
            (TRAIN_RED, "red")
        } else {
            (TRAIN_EVICTED, "evicted")
        };
        let body = format!(
            "The land train found this ticket {verdict}: {}\n\nFix the cause, commit, and run `frob land --train` again; the ticket is still leased.",
            reason.unwrap_or("no reason recorded")
        );
        let ledger = &self.site.ws.ledger;
        if let Err(e) = ledger.comment(*id, CommentSubtype::Note, &body) {
            tracing::warn!(ticket = %id, error = %e, "train result not written to the ticket");
            return;
        }
        let patch = Patch {
            add_labels: vec![label.to_owned()],
            remove_labels: vec![other_label(label).to_owned()],
            ..Patch::default()
        };
        if let Err(e) = ledger.update(*id, &patch) {
            tracing::warn!(ticket = %id, error = %e, "train label not set on the ticket");
        }
    }

    /// Select up to `size` mutually disjoint tickets from the queue, oldest first.
    fn select(&self, size: usize, report: &mut RoundReport) -> Result<Vec<Chosen>, LandError> {
        let mut chosen: Vec<Chosen> = Vec::new();
        for entry in self.site.store.queue()? {
            if chosen.len() >= size {
                break;
            }
            let handle = entry.id.to_string();
            match self.load(&entry)? {
                Err(Unfit::Closed) => {
                    tracing::info!(ticket = %handle, "queued ticket already closed; settled as landed");
                    self.settle(
                        &entry.id,
                        &report.run,
                        MemberStatus::Landed,
                        Some("already closed".to_owned()),
                    )?;
                }
                Err(Unfit::Evict(reason)) => {
                    tracing::warn!(ticket = %handle, %reason, "queued ticket evicted");
                    report.evicted.push(format!("{handle}: {reason}"));
                    self.settle(&entry.id, &report.run, MemberStatus::Evicted, Some(reason))?;
                }
                Ok(c) => {
                    let mut clash = false;
                    for other in &chosen {
                        if scopes_overlap(&other.scope, &c.scope)? {
                            clash = true;
                            break;
                        }
                    }
                    if clash {
                        tracing::info!(ticket = %c.pre.handle, "scope overlaps a chosen ticket; left queued");
                        report.skipped.push(c.pre.handle.clone());
                    } else {
                        chosen.push(c);
                    }
                }
            }
        }
        Ok(chosen)
    }

    /// Evict every chosen member that does not merge onto the base, with git's reason.
    ///
    /// A merge conflict is the member's own fault, not the round's: it is settled `Evicted` and the
    /// rest of the batch proceeds (a dry candidate build in merge order finds them).
    fn evict_unmergeable(
        &self,
        base_oid: &str,
        chosen: &mut Vec<Chosen>,
        report: &mut RoundReport,
    ) -> Result<(), LandError> {
        if chosen.is_empty() {
            return Ok(());
        }
        let members: Vec<CandidateMember> = chosen.iter().map(member_of).collect();
        let candidate = build_candidate(
            &self.site.repo,
            &self.site.primary,
            &format!("screen-{}", report.run),
            base_oid,
            &members,
        )?;
        for s in &candidate.skipped {
            let Some(c) = chosen.iter().find(|c| c.pre.handle == s.handle) else {
                continue;
            };
            let reason = format!("did not merge onto the base: {}", s.reason);
            tracing::warn!(ticket = %s.handle, %reason, "train member evicted");
            report.evicted.push(format!("{}: {reason}", s.handle));
            self.settle(&c.pre.id, &report.run, MemberStatus::Evicted, Some(reason))?;
        }
        let gone: Vec<String> = candidate.skipped.iter().map(|s| s.handle.clone()).collect();
        chosen.retain(|c| !gone.contains(&c.pre.handle));
        Ok(())
    }

    /// A fresh run id, unique across drivers and rounds.
    fn run_id(&mut self) -> String {
        self.seq += 1;
        format!(
            "train-{}-{}-{}",
            std::process::id(),
            self.clock.now().unix(),
            self.seq
        )
    }

    /// Plan the batch: which tickets can land and which are culprits.
    fn plan(&self, base_oid: &str, chosen: &[Chosen]) -> Plan {
        let batch: Vec<String> = chosen.iter().map(|c| c.pre.handle.clone()).collect();
        if let Some(r) = &self.opts.runner {
            return bisect::plan(&batch, &[], &DynRunner(r.as_ref()));
        }
        let backend = GitBackend {
            primary: self.site.primary.clone(),
            base_oid: base_oid.to_owned(),
            ledger: self.site.ws.ledger.config().clone(),
            members: chosen.iter().map(member_of).collect(),
            worktrees: chosen
                .iter()
                .map(|c| (c.pre.handle.clone(), c.pre.wt_path.clone()))
                .collect::<HashMap<_, _>>(),
            round: Mutex::new(0),
            stored: chosen
                .iter()
                .filter_map(|c| c.entry.rules.clone().map(|r| (c.pre.handle.clone(), r)))
                .collect(),
        };
        let infos = chosen
            .iter()
            .map(|c| MemberInfo {
                handle: c.pre.handle.clone(),
                scope: c.scope.clone(),
                cone: c.scope.clone(),
                paths: c.paths.clone(),
            })
            .collect();
        let checker = CandidateChecker::new(backend, infos);
        bisect::plan_with(&batch, &|| checker.suspects(), &checker)
    }

    /// Close `run` over `landable`, then release each landed member and record its result.
    fn close(
        &self,
        run: &mut TrainRun,
        landable: &[&Chosen],
        report: &mut RoundReport,
    ) -> Result<Vec<(TicketId, String)>, LandError> {
        let members: Vec<CloseMember> = landable
            .iter()
            .map(|c| CloseMember {
                id: c.pre.id,
                branch: c.pre.branch.clone(),
                evidence: c.pre.evidence.clone(),
                done: c.pre.done.clone(),
            })
            .collect();
        let closer = TrainCloser {
            repo: &self.site.repo,
            primary: &self.site.primary,
            ledger: &self.site.ws.ledger,
            store: &self.site.store,
            base: &self.site.base,
            opts: &self.opts.land,
            ci_override: self.opts.land.override_base_ci.as_deref(),
        };
        let done = closer.close_run(run, &members)?;
        for id in &done.landed {
            let Some(c) = landable.iter().find(|c| c.pre.id == *id) else {
                continue;
            };
            let removed = finish_member(
                &self.site.primary,
                &c.pre,
                self.opts.land.keep_worktree,
                &self.site.base,
                self.clock,
                &mut report.warnings,
            )?;
            tracing::info!(ticket = %c.pre.handle, worktree_removed = removed, "train member landed");
            report.landed.push(c.pre.handle.clone());
            self.settle(id, &run.id, MemberStatus::Landed, None)?;
        }
        Ok(done.pending)
    }

    /// Finish a run an earlier driver left behind, or discard it when its candidate never reached the base.
    fn recover(&mut self) -> Result<(), LandError> {
        let Some(mut run) = self.site.store.load_run()? else {
            return Ok(());
        };
        let in_base = match &run.candidate_oid {
            Some(c) => {
                self.site
                    .repo
                    .merge_base(&base_ref(&self.site.base), c)?
                    .map(|o| o.to_string())
                    == Some(c.clone())
            }
            None => false,
        };
        let phase = resume_phase(&run, in_base);
        tracing::warn!(run = %run.id, ?phase, in_base, "recovering a train run left behind");
        if matches!(phase, Phase::Advanced | Phase::Closing) {
            let queue = self.site.store.queue()?;
            let mut loaded: Vec<Chosen> = Vec::new();
            for m in run
                .members
                .iter()
                .filter(|m| m.status == MemberStatus::Green)
            {
                if let Some(Ok(c)) = queue
                    .iter()
                    .find(|e| e.id == m.id)
                    .map(|e| self.load(e))
                    .transpose()?
                {
                    loaded.push(c);
                }
            }
            let refs: Vec<&Chosen> = loaded.iter().collect();
            let mut report = RoundReport {
                run: run.id.clone(),
                ..RoundReport::default()
            };
            let pending = self.close(&mut run, &refs, &mut report)?;
            if let Some((id, why)) = pending.first() {
                return Err(pending_error(id, why));
            }
        } else {
            self.site.store.clear_run()?;
        }
        Ok(())
    }

    #[allow(clippy::too_many_lines)] // one linear pipeline: select, check, hand back, close, adapt
    /// Run one round: select, plan, close what is green, hand culprits back.
    fn round(&mut self) -> Result<RoundReport, LandError> {
        let store = &self.site.store;
        let batch = store.batch()?;
        let cap = self.site.cfg.train_max.max(1);
        let size = batch.current.min(cap).max(1);
        let mut report = RoundReport {
            run: self.run_id(),
            batch_size: size,
            ..RoundReport::default()
        };
        if self.opts.land.push {
            report.warnings.push(
                "--push is not applied by the land train; push the base afterwards".to_owned(),
            );
        }
        self.ci.reset();
        self.lock.progress("train-select");
        let mut chosen = self.select(size as usize, &mut report)?;
        let base_oid = self
            .site
            .repo
            .rev_parse(&base_ref(&self.site.base))?
            .to_string();
        self.evict_unmergeable(&base_oid, &mut chosen, &mut report)?;
        report.considered = chosen.iter().map(|c| c.pre.handle.clone()).collect();
        if chosen.is_empty() {
            tracing::info!(run = %report.run, "nothing ready to land");
            return Ok(report);
        }
        tracing::info!(run = %report.run, size, members = chosen.len(), %base_oid, "train round planned");

        self.lock.progress("train-check");
        let plan = self.plan(&base_oid, &chosen);
        report.checks = plan.checks;
        if plan.fault.is_some() || !plan.unchecked.is_empty() {
            let why = plan
                .fault
                .map_or_else(|| "tickets could not be checked".to_owned(), |f| f.message);
            tracing::error!(run = %report.run, %why, "train check faulted; members stay queued");
            return Err(needs_action(
                "E-LAND-TRAIN-FAULT",
                format!("the land train could not check its candidate: {why}"),
                "fix the environment and run `frob train run` again; the tickets are still queued",
            ));
        }

        for culprit in &plan.culprits {
            let Some(c) = chosen.iter().find(|c| c.pre.handle == culprit.handle) else {
                continue;
            };
            tracing::warn!(ticket = %culprit.handle, "train culprit returned to its agent");
            self.settle(
                &c.pre.id,
                &report.run,
                MemberStatus::Red,
                Some(culprit.evidence.clone()),
            )?;
            report.culprits.push(CulpritReport {
                handle: culprit.handle.clone(),
                evidence: culprit.evidence.clone(),
            });
        }

        let landable: Vec<&Chosen> = chosen
            .iter()
            .filter(|c| plan.landable.contains(&c.pre.handle))
            .collect();
        let mut pending = Vec::new();
        if !landable.is_empty() {
            self.lock.progress("train-close");
            let members: Vec<CandidateMember> = landable.iter().map(|c| member_of(c)).collect();
            let candidate = build_candidate(
                &self.site.repo,
                &self.site.primary,
                &format!("final-{}", report.run),
                &base_oid,
                &members,
            )?;
            if let Some(s) = candidate.skipped.first() {
                return Err(LandError::Config(format!(
                    "{} did not merge into the verified candidate: {}",
                    s.handle, s.reason
                )));
            }
            let mut run = TrainRun::new(
                report.run.clone(),
                base_oid,
                landable
                    .iter()
                    .map(|c| Member {
                        id: c.pre.id,
                        head_oid: c.entry.head_oid.clone(),
                        status: MemberStatus::Green,
                        reason: None,
                    })
                    .collect(),
            );
            run.candidate_oid = Some(candidate.oid.clone());
            run.phase = Phase::Checking;
            self.site.store.save_run(&mut run)?;
            pending = self.close(&mut run, &landable, &mut report)?;
            drop(candidate);
        }

        if let Some((id, why)) = pending.first() {
            return Err(pending_error(id, why));
        }
        let outcome = if report.culprits.is_empty() {
            SizeOutcome::Green
        } else {
            SizeOutcome::Red
        };
        let next = batch_size::next_size(size as usize, outcome, cap as usize);
        let next = u32::try_from(next).unwrap_or(cap).clamp(1, cap);
        self.site.store.set_batch(&BatchSize {
            current: next,
            max: cap,
        })?;
        tracing::info!(run = %report.run, landed = report.landed.len(), culprits = report.culprits.len(), next, "train round done");
        Ok(report)
    }

    /// Recover a stale run, then run rounds until the queue is empty or a round makes no progress.
    fn drain(&mut self, rounds: Option<u32>) -> Result<TrainRunReport, LandError> {
        self.recover()?;
        let mut out = Vec::new();
        loop {
            if self.site.store.queue()?.is_empty() {
                break;
            }
            let round = self.round();
            self.flush_handbacks();
            let report = round?;
            let moved = report.progressed();
            out.push(report);
            if !moved || rounds.is_some_and(|n| out.len() >= n as usize) {
                break;
            }
        }
        let pruned = self.site.store.prune_results(KEEP_RESULTS)?;
        let remaining = self.site.store.queue()?.len();
        tracing::info!(rounds = out.len(), remaining, pruned, "train drained");
        Ok(TrainRunReport {
            rounds: out,
            remaining,
        })
    }
}

/// The candidate-builder view of a chosen ticket.
fn member_of(c: &Chosen) -> CandidateMember {
    CandidateMember {
        handle: c.pre.handle.clone(),
        branch: c.pre.branch.clone(),
        scope: c.scope.clone(),
        oid: c.entry.head_oid.clone(),
    }
}

/// The refusal for a member whose close failed after the base advanced.
fn pending_error(id: &TicketId, why: &str) -> LandError {
    needs_action(
        "E-LAND-TRAIN-PENDING",
        format!("ticket {id} is in the base but could not be closed: {why}"),
        "run `frob train run` again to finish closing it",
    )
}

/// The verb error when the train is switched off.
fn disabled() -> LandError {
    needs_action(
        "E-LAND-TRAIN-OFF",
        "the land train is disabled ([land] train = false)",
        "land one ticket at a time with `frob land`, or set [land] train = true",
    )
}

/// Run one round of the train (`frob train run`).
///
/// # Errors
///
/// `E-LAND-TRAIN-OFF`, `E-LAND-LOCKED` past `--wait`, `E-LAND-TRAIN-FAULT` when the candidate
/// could not be checked, `E-LAND-TRAIN-PENDING` when a landed member could not be closed, and
/// git, ledger and state failures.
pub fn train_run(
    root: &Path,
    opts: &TrainOptions,
    clock: &Arc<dyn Clock>,
) -> Result<TrainRunReport, LandError> {
    drive(root, opts, clock, Some(1))
}

/// Run rounds until the queue is empty (`frob train drain`); errors as [`train_run`].
///
/// # Errors
///
/// As [`train_run`].
pub fn train_drain(
    root: &Path,
    opts: &TrainOptions,
    clock: &Arc<dyn Clock>,
) -> Result<TrainRunReport, LandError> {
    drive(root, opts, clock, None)
}

/// Take the lock and drive up to `rounds` rounds.
fn drive(
    root: &Path,
    opts: &TrainOptions,
    clock: &Arc<dyn Clock>,
    rounds: Option<u32>,
) -> Result<TrainRunReport, LandError> {
    let site = Site::open(root, clock)?;
    if !site.cfg.train {
        return Err(disabled());
    }
    drop(site);
    let wait = Duration::from_secs(opts.land.wait_secs);
    Driver::start(root, opts, clock, wait)?.drain(rounds)
}

/// Report the train without taking the lock (`frob train status`).
///
/// # Errors
///
/// Git, config and state-store failures.
pub fn train_status(root: &Path, clock: &Arc<dyn Clock>) -> Result<TrainStatusReport, LandError> {
    let site = Site::open(root, clock)?;
    let status = site.store.status()?;
    let queue = site.store.queue()?;
    let batch = site.store.batch()?;
    tracing::info!(
        queued = queue.len(),
        batch = batch.current,
        "train status read"
    );
    Ok(TrainStatusReport {
        summary: status.summary,
        enabled: site.cfg.train,
        queue,
        current: status.run,
        batch,
        live: status.live,
        stale: status.stale,
    })
}

/// What [`enqueue`] did.
pub enum Enqueued {
    /// The ticket needed no train (already done).
    Done(Box<LandOutcome>),
    /// The ticket is waiting in the queue.
    Queued {
        /// The ticket.
        id: TicketId,
    },
}

/// Put the ticket of `opts` on the train queue after its ticket-local preconditions hold.
///
/// # Errors
///
/// The refusals of the land preconditions (not leased, dirty, unbound criteria, red base CI) and
/// state-store failures.
pub fn enqueue(
    root: &Path,
    opts: &LandOptions,
    clock: &Arc<dyn Clock>,
) -> Result<Enqueued, LandError> {
    let begun = begin(root, opts, clock)?;
    if begun.view.summary.category == frob_ledger::model::Category::Done {
        return Ok(Enqueued::Done(Box::new(already_done(
            &begun.view,
            begun.id,
            &begun.handle,
            &begun.base,
            opts,
        ))));
    }
    let Begun {
        repo,
        cwd_root,
        here,
        leases,
        view,
        id,
        base,
        ..
    } = begun;
    let pre = preconditions(repo, &cwd_root, here, &leases, &view, &base, opts)?;
    let head = pre.wt.rev_parse(&pre.branch)?;
    let rules = enqueue_rules(&pre)?;
    let store = TrainStore::new(pre.repo.common_dir());
    store.clear_result(&id)?;
    store.enqueue(&QueueEntry {
        schema_version: SCHEMA_VERSION,
        id,
        enqueued_at: clock.now().unix(),
        actor: pre.site.ledger.actor()?,
        worktree: pre.wt_path.display().to_string(),
        head_oid: head.to_string(),
        rules: Some(rules),
    })?;
    mark_queued(&pre.primary, clock, id, true);
    clear_result_labels(&pre.site.ledger, id);
    tracing::info!(ticket = %pre.handle, %head, "ticket enqueued on the land train");
    Ok(Enqueued::Queued { id })
}

/// Run the ticket's cheap rules at enqueue (in the agent's process, outside the land lock).
///
/// A ticket new-red on its own rules is refused here, before it takes a queue slot; otherwise the raw
/// blocking findings are returned for the queue entry, and the driver re-ratchets them rather than re-run.
fn enqueue_rules(pre: &crate::land::Preconditions) -> Result<Vec<FindingNote>, LandError> {
    let ledger = pre.site.ledger.config().clone();
    let base_oid = pre.base_oid.to_string();
    let raw = run_member_rules(&pre.wt_path, &pre.handle, &base_oid, &ledger)?;
    let base = ratchet::base_findings(&pre.wt, &pre.wt_path, &base_oid, &ledger)?;
    let new = ratchet::without_base(raw.clone(), &base);
    if !new.is_empty() {
        let lines: Vec<String> = new
            .iter()
            .map(|n| {
                format!(
                    "{} {}: {}",
                    n.rule,
                    n.path.as_deref().unwrap_or("-"),
                    n.message
                )
            })
            .collect();
        tracing::warn!(ticket = %pre.handle, red = new.len(), "enqueue refused: ticket rules red");
        return Err(needs_action(
            "E-LAND-CHECK-RED",
            format!(
                "{} is red on its own ticket rules: {}",
                pre.handle,
                lines.join("; ")
            ),
            "fix the findings above, commit, and run `frob land --train` again",
        ));
    }
    tracing::info!(ticket = %pre.handle, raw = raw.len(), "ticket rules ran at enqueue");
    Ok(raw)
}

/// The outcome of a ticket the train landed, read back from the ledger.
fn landed_outcome(
    root: &Path,
    clock: &Arc<dyn Clock>,
    id: TicketId,
    opts: &LandOptions,
) -> Result<LandOutcome, LandError> {
    let site = Site::open(root, clock)?;
    let view = site.ws.ledger.show(id)?;
    let mut out = blank_outcome(id, &view.summary.handle, &site.base, opts);
    out.closed = true;
    out.outcome = Some(view.ticket.front.outcome.unwrap_or(opts.outcome));
    out.worktree_removed = !opts.keep_worktree;
    Ok(out)
}

/// Land the ticket of `opts` through the train (`frob land --train`).
///
/// The ticket is enqueued; this call then waits (up to `--wait` seconds) for the train to land it,
/// driving the train itself when no other driver holds the lock. A lone ticket, a dry run, a done
/// ticket or `[land] train = false` use the plain [`land`].
///
/// # Errors
///
/// As [`land`]; a ticket the train found red returns `E-LAND-CHECK-RED` with the failing evidence
/// and one the train evicted returns `E-LAND-TRAIN-EVICTED`.
pub fn land_train(
    root: &Path,
    opts: &TrainOptions,
    clock: &Arc<dyn Clock>,
) -> Result<LandOutcome, LandError> {
    let probe = begin(root, &opts.land, clock)?;
    let cfg = read_config(&probe.repo, &probe.base)?;
    if opts.land.dry_run || !cfg.train {
        tracing::info!(
            train = cfg.train,
            dry_run = opts.land.dry_run,
            "land --train uses the plain land"
        );
        return land(root, &opts.land, clock);
    }
    let (id, handle, common) = (
        probe.id,
        probe.handle.clone(),
        probe.repo.common_dir().to_path_buf(),
    );
    drop(probe);
    if let Enqueued::Done(out) = enqueue(root, &opts.land, clock)? {
        return Ok(*out);
    }
    if opts.enqueue_only {
        tracing::info!(ticket = %handle, "enqueue-only: queued without driving");
        return Ok(queued_outcome(id, &handle, &opts.land));
    }
    let store = TrainStore::new(&common);
    let deadline = Instant::now() + Duration::from_secs(opts.land.wait_secs);
    loop {
        if let Some(result) = store.result(&id)? {
            return result_to_outcome(root, clock, &opts.land, &handle, &result);
        }
        match Driver::start(root, opts, clock, Duration::ZERO) {
            Ok(mut driver) => {
                let alone = driver.site.store.queue()?.iter().all(|e| e.id == id)
                    && driver.site.store.load_run()?.is_none();
                if alone {
                    tracing::info!(ticket = %handle, "alone on the train; landing it directly");
                    driver.site.store.dequeue(&id)?;
                    mark_queued(&driver.site.primary, clock, id, false);
                    drop(driver);
                    return land(root, &opts.land, clock);
                }
                let report = driver.drain(None)?;
                drop(driver);
                if let Some(result) = store.result(&id)? {
                    return result_to_outcome(root, clock, &opts.land, &handle, &result);
                }
                if report.rounds.iter().all(|r| !r.progressed()) && Instant::now() >= deadline {
                    return Ok(queued_outcome(id, &handle, &opts.land));
                }
            }
            Err(e) if is_locked(&e) => {
                if Instant::now() >= deadline {
                    return Ok(queued_outcome(id, &handle, &opts.land));
                }
            }
            Err(e) => return Err(e),
        }
        if Instant::now() >= deadline {
            return Ok(queued_outcome(id, &handle, &opts.land));
        }
        std::thread::sleep(POLL);
    }
}

/// The outcome of a ticket still waiting on the train when the wait ran out.
fn queued_outcome(id: TicketId, handle: &str, opts: &LandOptions) -> LandOutcome {
    let mut out = blank_outcome(id, handle, "-", opts);
    out.warnings.push(
        "queued on the land train; it lands when a driver runs the train (`frob train run`) or this command is repeated with --wait"
            .to_owned(),
    );
    out
}

/// Turn a recorded result into the land outcome or the refusal the enqueuer sees.
fn result_to_outcome(
    root: &Path,
    clock: &Arc<dyn Clock>,
    opts: &LandOptions,
    handle: &str,
    result: &TicketResult,
) -> Result<LandOutcome, LandError> {
    let reason = result.reason.clone().unwrap_or_default();
    match result.status {
        MemberStatus::Landed => landed_outcome(root, clock, result.id, opts),
        MemberStatus::Red => Err(needs_action(
            "E-LAND-CHECK-RED",
            format!("the land train found {handle} red: {reason}"),
            "fix the failures above, commit, and run `frob land --train` again; the ticket is still leased",
        )),
        _ => Err(needs_action(
            "E-LAND-TRAIN-EVICTED",
            format!("the land train dropped {handle}: {reason}"),
            "fix the cause and run `frob land --train` again",
        )),
    }
}
