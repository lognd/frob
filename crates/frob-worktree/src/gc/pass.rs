//! The pass: decide whether to run, collect each category within a time bound, and report.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use gob_git::Repo;
use schemars::JsonSchema;
use serde::Serialize;

use super::adapter::{self, BuildAdapter, BuildPolicy};
use super::cargo::CargoAdapter;
use super::config::{GIB, GcConfig, MIB};
use super::git::git;
use super::jail::Jail;
use super::removing;
use super::scan::scan;
use super::stamp::{self, Stamp, Usage};
use super::worktrees::{self, Decision, WorktreeEnv};
use super::{artifacts, caches};

/// Warnings kept in a report; more are counted, not listed.
const MAX_WARNINGS: usize = 20;
/// A leftover ratchet base checkout older than this is abandoned and removed.
const LAND_BASE_MAX_AGE: Duration = Duration::from_secs(3600);

/// Whether a ticket still needs its worktree.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TicketState {
    /// Not done: its work may still be unsaved.
    Open,
    /// Done (any outcome).
    Closed,
    /// The ledger does not know it, or could not be read.
    Unknown,
}

/// What the pass asks the ledger.
pub trait TicketOracle {
    /// The state of the ticket with this `~handle`.
    fn state(&self, handle: &str) -> TicketState;

    /// Digests mentioned by open tickets' events, or `None` when they cannot be read (then no blob is removed).
    fn referenced_digests(&self) -> Option<BTreeSet<String>>;
}

/// How the pass was asked to run.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    /// Throttled by the interval, forced by the disk guard.
    Auto,
    /// Unthrottled (`frob doctor --fix`).
    Forced,
    /// Plan and report only; nothing is removed and the stamp is untouched.
    DryRun,
}

/// Everything a pass reads, borrowed from the calling verb.
pub struct Env<'a> {
    /// The repository.
    pub repo: &'a Repo,
    /// The primary checkout.
    pub primary: &'a Path,
    /// The directory ticket worktrees live in.
    pub worktree_parent: &'a Path,
    /// Short name of the base branch.
    pub base: &'a str,
    /// `[gc]`.
    pub config: &'a GcConfig,
    /// Ticket knowledge.
    pub tickets: &'a dyn TicketOracle,
    /// Worktree paths held by live leases.
    pub live_worktrees: &'a [PathBuf],
    /// The current time.
    pub now: SystemTime,
    /// Free bytes of the volume holding a path (injected so tests control the guard).
    pub free_bytes: &'a dyn Fn(&Path) -> Option<u64>,
    /// Build-output adapters.
    pub adapters: &'a [&'a dyn BuildAdapter],
}

/// The adapters frob ships: Cargo.
pub fn default_adapters() -> [&'static dyn BuildAdapter; 1] {
    static CARGO: CargoAdapter = CargoAdapter;
    [&CARGO]
}

/// One thing the pass removed (or, in a dry run, would remove).
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct Action {
    /// `worktrees`, `removing`, `build`, `caches`, `artifacts` or `land-base`.
    pub category: String,
    /// What it is, as a path.
    pub target: String,
    /// Bytes reclaimed.
    pub bytes: u64,
}

/// Something the pass deliberately left alone, and why.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct Kept {
    /// What it is.
    pub target: String,
    /// Why it stays.
    pub reason: String,
}

/// The outcome of one pass.
#[derive(Debug, Clone, Default, Serialize, JsonSchema)]
pub struct Report {
    /// True when the pass collected (or, dry, planned); false when it was skipped.
    pub ran: bool,
    /// True for a dry run: the figures are what a pass would reclaim.
    pub dry_run: bool,
    /// Why nothing ran, when `ran` is false.
    pub skipped: Option<String>,
    /// True when the disk guard overrode the interval.
    pub forced_by_guard: bool,
    /// Free bytes seen at the start, when measurable.
    pub free_bytes: Option<u64>,
    /// Bytes reclaimed (a dry run: that would be).
    pub reclaimed_bytes: u64,
    /// Removals.
    pub actions: Vec<Action>,
    /// Things kept on purpose, with reasons.
    pub kept: Vec<Kept>,
    /// Usage per category after the pass.
    pub usage: Vec<Usage>,
    /// Non-fatal problems.
    pub warnings: Vec<String>,
    /// Milliseconds the pass took.
    pub elapsed_ms: u64,
}

/// A wall-clock bound checked between units of work.
struct Deadline {
    at: Instant,
    hit: bool,
}

impl Deadline {
    fn expired(&mut self) -> bool {
        if Instant::now() >= self.at {
            self.hit = true;
        }
        self.hit
    }
}

/// Mutable state of one pass.
struct Run<'a> {
    env: &'a Env<'a>,
    dry: bool,
    deadline: Deadline,
    report: Report,
    suppressed: usize,
}

impl Run<'_> {
    fn warn(&mut self, msg: impl Into<String>) {
        let msg = msg.into();
        tracing::warn!(warning = %msg, "gc warning");
        if self.report.warnings.len() < MAX_WARNINGS {
            self.report.warnings.push(msg);
        } else {
            self.suppressed += 1;
        }
    }

    fn did(&mut self, category: &str, target: &Path, bytes: u64) {
        self.report.reclaimed_bytes = self.report.reclaimed_bytes.saturating_add(bytes);
        self.report.actions.push(Action {
            category: category.to_owned(),
            target: target.display().to_string(),
            bytes,
        });
    }

    fn kept(&mut self, target: &Path, reason: impl Into<String>) {
        self.report.kept.push(Kept {
            target: target.display().to_string(),
            reason: reason.into(),
        });
    }
}

fn unix(t: SystemTime) -> i64 {
    t.duration_since(UNIX_EPOCH)
        .map_or(0, |d| i64::try_from(d.as_secs()).unwrap_or(i64::MAX))
}

/// The host's report-only setting; Windows reports without deleting in the automatic pass.
const REPORT_ONLY_HOST: bool = cfg!(windows);

/// True when `mode` must only report: the automatic pass on Windows until the jail fix is proven (~EDPHHFS).
pub const fn report_only(mode: Mode, windows: bool) -> bool {
    windows && matches!(mode, Mode::Auto)
}

/// Run one pass in `mode`; never fails, problems are warnings in the report.
pub fn run(env: &Env<'_>, mode: Mode) -> Report {
    let started = Instant::now();
    let dry = mode == Mode::DryRun || report_only(mode, REPORT_ONLY_HOST);
    if dry && mode != Mode::DryRun {
        tracing::warn!("automatic gc is report-only on this platform; nothing is deleted");
    }
    let common = env.repo.common_dir().to_path_buf();
    let stamp = stamp::load(&common);
    let free = (env.free_bytes)(env.primary);
    let guard_bytes = env.config.guard_min_free_gb.saturating_mul(GIB);
    let guard = guard_bytes > 0 && free.is_some_and(|f| f < guard_bytes);
    let mut report = Report {
        dry_run: dry,
        forced_by_guard: false,
        free_bytes: free,
        ..Report::default()
    };
    if mode == Mode::Auto {
        if !env.config.enabled {
            report.skipped = Some("gc is disabled in [gc] enabled".to_owned());
        } else if guard {
            report.forced_by_guard = true;
        } else if !stamp.due(unix(env.now), env.config.interval_secs) {
            report.skipped = Some("a pass ran within [gc] interval_secs".to_owned());
        }
        if let Some(why) = &report.skipped {
            tracing::debug!(why, "gc pass skipped");
            return report;
        }
    }
    report.ran = true;
    let mut run = Run {
        env,
        dry,
        deadline: Deadline {
            at: started + Duration::from_secs(env.config.time_limit_secs.max(1)),
            hit: false,
        },
        report,
        suppressed: 0,
    };
    let usage = collect(&mut run);
    if run.deadline.hit {
        run.warn("time limit reached; the rest waits for the next pass");
    }
    if run.suppressed > 0 {
        let n = run.suppressed;
        run.report
            .warnings
            .push(format!("{n} more warning(s) not listed"));
    }
    run.report.usage = usage;
    run.report.elapsed_ms = u64::try_from(started.elapsed().as_millis()).unwrap_or(u64::MAX);
    if mode != Mode::DryRun {
        let next = Stamp {
            last_run_unix: unix(env.now),
            last_reclaimed_bytes: run.report.reclaimed_bytes,
            total_reclaimed_bytes: stamp
                .total_reclaimed_bytes
                .saturating_add(run.report.reclaimed_bytes),
            passes: stamp.passes + 1,
            usage: run.report.usage.clone(),
        };
        if let Err(e) = stamp::save(&common, &next) {
            run.warn(format!("gc stamp not saved: {e}"));
        }
    }
    tracing::info!(
        reclaimed = run.report.reclaimed_bytes,
        actions = run.report.actions.len(),
        kept = run.report.kept.len(),
        warnings = run.report.warnings.len(),
        dry_run = run.dry,
        forced_by_guard = run.report.forced_by_guard,
        elapsed_ms = run.report.elapsed_ms,
        "gc pass finished"
    );
    run.report
}

/// All categories in order; returns the usage per category after collection.
fn collect(run: &mut Run<'_>) -> Vec<Usage> {
    let env = run.env;
    let common = env.repo.common_dir().to_path_buf();
    let wt_jail = Jail::new([env.worktree_parent.to_path_buf()]);
    let live = env.live_worktrees;
    let cwd = std::env::current_dir().ok();
    let wenv = WorktreeEnv {
        repo: env.repo,
        primary: env.primary,
        parent: env.worktree_parent,
        base: env.base,
        live,
        tickets: env.tickets,
        jail: &wt_jail,
        cwd,
    };
    if env.config.worktrees {
        collect_worktrees(run, &wenv);
    }
    if !run.deadline.expired() {
        collect_removing(run);
    }
    let state_jail = Jail::new([common.join("frob")]);
    if !run.deadline.expired() {
        collect_land_base(run, &common, &state_jail);
    }
    let checkouts = checkouts(env, &wenv);
    let (build_usage, build_by_checkout) = collect_build(run, &checkouts);
    collect_caches(run, &checkouts, &common, &state_jail);
    if !run.deadline.expired() {
        collect_artifacts(run, &common, &state_jail);
    }
    let mut usage = vec![Usage {
        category: "build".to_owned(),
        bytes: build_usage,
    }];
    let mut wt_bytes = 0u64;
    for (path, build) in &build_by_checkout {
        if path != env.primary {
            wt_bytes += scan(path).bytes.saturating_sub(*build);
        }
    }
    usage.push(Usage {
        category: "worktrees".to_owned(),
        bytes: wt_bytes,
    });
    usage.push(Usage {
        category: "caches".to_owned(),
        bytes: checkouts
            .iter()
            .map(|c| caches::total(&caches::entries(c)))
            .sum::<u64>()
            + caches::total(&caches::shared_entries(&common)),
    });
    usage.push(Usage {
        category: "artifacts".to_owned(),
        bytes: artifacts::usage(&common),
    });
    usage.push(Usage {
        category: "land-base".to_owned(),
        bytes: land_base_dirs(&common).iter().map(|d| scan(d).bytes).sum(),
    });
    usage
}

/// The primary and every linked worktree under the frob worktree parent that still exists.
fn checkouts(env: &Env<'_>, wenv: &WorktreeEnv<'_>) -> Vec<PathBuf> {
    let mut out = vec![env.primary.to_path_buf()];
    let parent = gob_exec::canonical(wenv.parent).ok();
    if let Ok(infos) = env.repo.list_worktrees() {
        for i in infos {
            let canon = gob_exec::canonical(&i.path).ok();
            let primary = gob_exec::canonical(env.primary).ok();
            if canon.is_some()
                && canon != primary
                && canon
                    .as_deref()
                    .zip(parent.as_deref())
                    .is_some_and(|(c, p)| c.starts_with(p))
            {
                out.push(i.path);
            }
        }
    }
    out
}

fn collect_worktrees(run: &mut Run<'_>, wenv: &WorktreeEnv<'_>) {
    let mut removed_any = false;
    for cand in worktrees::assess(wenv) {
        if run.deadline.expired() {
            break;
        }
        match &cand.decision {
            Decision::Keep(why) => {
                if why.contains("uncommitted")
                    || why.contains("unpushed")
                    || why.contains("not in the ledger")
                {
                    run.kept(&cand.path, why.clone());
                } else {
                    tracing::debug!(path = %cand.path.display(), why, "gc kept worktree");
                }
            }
            Decision::Remove { .. } if run.dry => {
                let bytes = scan(&cand.path).bytes;
                run.did("worktrees", &cand.path, bytes);
            }
            Decision::Remove { .. } => match worktrees::remove(wenv, &cand) {
                Ok(bytes) => {
                    removed_any = true;
                    run.did("worktrees", &cand.path, bytes);
                }
                Err(e) => run.warn(e),
            },
        }
    }
    if removed_any {
        worktrees::prune(wenv);
    }
}

// frob:ticket 01M4HF7GJZZ2EX5JNABSVTM10F
/// Delete unregistered `*.removing` directories a land left behind (its background deletion died with it).
fn collect_removing(run: &mut Run<'_>) {
    let env = run.env;
    let dirs = removing::leftovers(env.repo, env.worktree_parent);
    if dirs.is_empty() {
        return;
    }
    if run.dry {
        for d in &dirs {
            let bytes = scan(d).bytes;
            run.did("removing", d, bytes);
        }
        return;
    }
    let (done, failed) = removing::sweep(env.worktree_parent, &dirs);
    for (d, bytes) in done {
        run.did("removing", &d, bytes);
    }
    for f in failed {
        run.warn(f);
    }
}

fn land_base_dirs(common: &Path) -> Vec<PathBuf> {
    let Ok(rd) = std::fs::read_dir(common.join("frob")) else {
        return Vec::new();
    };
    rd.filter_map(Result::ok)
        .filter(|e| e.file_name().to_string_lossy().starts_with("land-base-"))
        .filter(|e| e.file_type().is_ok_and(|t| t.is_dir()))
        .map(|e| e.path())
        .collect()
}

/// Remove abandoned ratchet base checkouts (`<common>/frob/land-base-*`) left by a crashed land.
fn collect_land_base(run: &mut Run<'_>, common: &Path, jail: &Jail) {
    let env = run.env;
    let mut removed_any = false;
    for dir in land_base_dirs(common) {
        let s = scan(&dir);
        let age = s
            .newest
            .and_then(|n| env.now.duration_since(n).ok())
            .unwrap_or_default();
        if age < LAND_BASE_MAX_AGE {
            tracing::debug!(dir = %dir.display(), "gc left a recent base checkout (a land may be running)");
            continue;
        }
        if run.dry {
            run.did("land-base", &dir, s.bytes);
            continue;
        }
        let Ok(canon) = jail.admit(&dir) else {
            run.warn(format!(
                "{} is not an admissible base checkout",
                dir.display()
            ));
            continue;
        };
        let text = canon.to_string_lossy().into_owned();
        // A real worktree registration must be dropped through git; the directory is then removed under the jail.
        let _ = git(
            env.repo,
            env.primary,
            &["worktree", "remove", "--force", &text],
        );
        if canon.exists()
            && let Err(e) = jail.remove(&canon)
        {
            run.warn(e);
            continue;
        }
        removed_any = true;
        run.did("land-base", &dir, s.bytes);
    }
    if removed_any {
        let _ = git(env.repo, env.primary, &["worktree", "prune"]);
    }
}

/// Plan and evict build output of every checkout; returns total bytes remaining and per-checkout build bytes.
fn collect_build(run: &mut Run<'_>, checkouts: &[PathBuf]) -> (u64, Vec<(PathBuf, u64)>) {
    let env = run.env;
    let cfg = env.config;
    let policy = BuildPolicy {
        incremental_max_age: Duration::from_secs(cfg.incremental_max_age_secs),
        keep_recent: Duration::from_secs(cfg.keep_recent_secs),
        budget_bytes: cfg.target_budget_gb.saturating_mul(GIB),
        keep_binaries: cfg.keep_binaries.clone(),
    };
    let mut remaining_total = 0u64;
    let mut per = Vec::new();
    for checkout in checkouts {
        let mut checkout_build = 0u64;
        for a in env.adapters {
            let dirs = a.output_dirs(checkout);
            let jail = Jail::new(dirs.clone());
            for dir in dirs {
                let Ok(canon) = gob_exec::canonical(&dir) else {
                    continue;
                };
                let units = a.units(&canon, &policy);
                let total = scan(&canon).bytes;
                let plan = adapter::plan(units, total, env.now, &policy);
                let mut left = plan.remaining_bytes;
                let mut stopped = false;
                for unit in &plan.evict {
                    if run.deadline.expired() {
                        stopped = true;
                        break;
                    }
                    if run.dry {
                        run.did("build", &canon.join(&unit.label), unit.bytes);
                        continue;
                    }
                    let mut ok = true;
                    for p in &unit.paths {
                        if let Err(e) = jail.remove(p) {
                            ok = false;
                            run.warn(e);
                        }
                    }
                    if ok {
                        run.did("build", &canon.join(&unit.label), unit.bytes);
                    } else {
                        left = left.saturating_add(unit.bytes);
                    }
                }
                if stopped {
                    left = total;
                }
                if plan.over_budget_kept_recent {
                    run.kept(
                        &canon,
                        format!(
                            "{} over budget; only the latest build's artifacts remain",
                            a.name()
                        ),
                    );
                }
                checkout_build += left;
            }
        }
        remaining_total += checkout_build;
        per.push((checkout.clone(), checkout_build));
    }
    (remaining_total, per)
}

fn collect_caches(run: &mut Run<'_>, checkouts: &[PathBuf], common: &Path, state_jail: &Jail) {
    let env = run.env;
    let budget = env.config.cache_budget_mb.saturating_mul(MIB);
    for checkout in checkouts {
        if run.deadline.expired() {
            return;
        }
        let jail = Jail::new([checkout.join(".frob")]);
        evict(run, &jail, caches::entries(checkout), budget);
    }
    // frob:ticket 01M42B6T28RX9PVM3X6TSK0M4Y
    if !run.deadline.expired() {
        evict(run, state_jail, caches::shared_entries(common), budget);
    }
}

/// Evict the least recently used of `entries` over `budget` through `jail`.
fn evict(run: &mut Run<'_>, jail: &Jail, entries: Vec<caches::Entry>, budget: u64) {
    let now = run.env.now;
    for e in caches::plan(entries, budget, now) {
        if run.dry {
            run.did("caches", &e.paths[0], e.bytes);
            continue;
        }
        let mut ok = true;
        for p in &e.paths {
            if let Err(err) = jail.remove(p) {
                ok = false;
                run.warn(err);
            }
        }
        if ok {
            run.did("caches", &e.paths[0], e.bytes);
        }
    }
}

fn collect_artifacts(run: &mut Run<'_>, common: &Path, jail: &Jail) {
    let env = run.env;
    let Some(referenced) = env.tickets.referenced_digests() else {
        run.warn("open tickets' evidence could not be read; no blob was removed");
        return;
    };
    let retention = Duration::from_secs(env.config.artifact_retention_days.saturating_mul(86_400));
    for blob in artifacts::plan(common, &referenced, retention, env.now) {
        if run.deadline.expired() {
            return;
        }
        if run.dry {
            run.did("artifacts", &blob.path, blob.bytes);
            continue;
        }
        match jail.remove(&blob.path) {
            Ok(_) => run.did("artifacts", &blob.path, blob.bytes),
            Err(e) => run.warn(e),
        }
    }
}
