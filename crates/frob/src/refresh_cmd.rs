//! The `refresh` verb: probe the configured remote for freshness and report the cached answer (`distributed-tickets.md` section 5).
//!
//! After a healthy probe the verb fetches only the changed refs (base and ledger branch), unions
//! the ledger into the local ref by plumbing, publishes it with a server-side compare-and-swap and
//! fast-forwards the base when that is safe (`distributed-tickets.md` sections 3.2, 4.6, 5.1).
//! `--status` reads the cache and never touches the network.

// frob:ticket 01M5CW046DKVK5QSJR8TMEN0F2
// frob:ticket 01M5CW049SPSRGGP5ENQD7BPB3
// frob:ticket 01M5CW04D5QJCJ5S72V8PE22M6

mod freshness;

use std::time::Duration;

use self::freshness::{FreshState, Notice, Signals, Thresholds, assess};
use frob_ledger::Ledger;
use frob_ledger::objects::integrate::Integration;
use gob_git::{MergeOutcome, RemoteRun, Repo};

use frob_ledger::RefMode;
use frob_ledger::refresh::{
    ProbeClass, ProbeMode, ProbeOutcome, ProbeReport, RefreshLock, RefreshState, probe,
};
use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};
use gob_diagnostics::{Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::FrobConfig;
use crate::workspace::{Located, config_refusal};

/// `refresh` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct RefreshArgs {
    #[arg(
        long,
        help = "Print the cached freshness line; no network, no state change"
    )]
    status: bool,
    #[arg(long, help = "Probe even inside the ttl or a failure backoff window")]
    force: bool,
    #[arg(
        long,
        help = "Start a detached refresh and return at once (used by git hooks)"
    )]
    background: bool,
}

/// Probe the remote for freshness (bounded, never prompts) or, with `--status`, print the cached one-line freshness.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "refresh",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Refresh {
    status: bool,
    force: bool,
    background: bool,
}

/// What `frob refresh` reports.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct RefreshReport {
    /// The one-line freshness, e.g. `frob:ok` or `frob:2h-stale`.
    pub status: String,
    /// `ok`, `offline`, `timeout`, `auth`, `rate`, `no-base` or `unknown`; `local-only` without a remote.
    pub class: String,
    /// `probed`, `cached`, `busy`, `local-only`, `status`, `background` or `skipped`.
    pub outcome: String,
    /// Whether any remote ref moved since the previous probe.
    pub changed: bool,
    /// The remote consulted.
    pub remote: String,
    /// The base branch required on it.
    pub base: String,
    /// Problem text, empty when ok.
    pub detail: String,
    /// What happened to the ledger ref: `none`, `unchanged`, `created`, `fast-forward`, `merged` or `conflict`.
    pub ledger: String,
    /// Whether the ledger branch was published to the remote.
    pub pushed: bool,
    /// What happened to the local base: `none`, `up-to-date`, `fast-forwarded`, `ahead`, `diverged` or `skipped-<why>`.
    pub base_sync: String,
    /// Paths the ledger union could not resolve.
    pub conflicts: Vec<String>,
    /// Seconds since the last probe; `None` when never probed or local-only.
    pub age_secs: Option<i64>,
    /// How the cached view relates to the remote: `fresh`, `stale`, `degraded`, `unknown` or `local-only`.
    pub freshness: FreshState,
    /// Ranked `W-SYNC-*` / `E-SYNC-*` notices, highest first; also in the envelope warnings.
    pub notices: Vec<Notice>,
}

/// Longest a fetch or push may run before it is killed (nothing changes when it is).
const FETCH_TIMEOUT: Duration = Duration::from_secs(10);

/// Re-integrate attempts after a lost compare-and-swap, local or remote.
const SYNC_ATTEMPTS: usize = 3;

impl Command for Refresh {
    type Data = RefreshReport;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<RefreshArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<RefreshArgs>(m)?;
        Ok(Self {
            status: a.status,
            force: a.force,
            background: a.background,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<RefreshReport> {
        let (repo, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
        let now = ctx.clock.now().unix();
        let base = cfg.tickets.r#ref.clone();
        if self.background && !self.status {
            return Ok(background(&repo, &root, &cfg, now));
        }
        if self.status {
            let state = RefreshState::load(repo.common_dir());
            tracing::debug!(class = ?state.class, "refresh --status from cache");
            let status = if repo.remote_url(&cfg.sync.remote).is_none() {
                "frob:local-only".to_owned()
            } else {
                state.status_line(now, cfg.sync.ttl_secs)
            };
            let has_remote = repo.remote_url(&cfg.sync.remote).is_some();
            let out = render(report(&state, status, "status", false));
            return Ok(with_freshness(
                out,
                &state,
                has_remote,
                Signals::default(),
                now,
                &cfg.sync,
            ));
        }
        let ledger = cfg.ledger();
        let ledger_branch = (ledger.mode == RefMode::Orphan).then_some(ledger.branch.as_str());
        let mode = if self.force {
            ProbeMode::Force
        } else {
            ProbeMode::Explicit
        };
        let done = probe(&repo, &cfg.sync, &base, ledger_branch, now, mode).map_err(|e| {
            CliError::from(Refusal::new(
                "E-SYNC-PROBE",
                RefusalClass::DomainNegative,
                e.to_string(),
            ))
        })?;
        tracing::info!(outcome = ?done.outcome, class = ?done.state.class, "refresh");
        let mut out = finish(&done, now, cfg.sync.ttl_secs)?;
        if done.state.class == ProbeClass::Ok
            && !matches!(done.outcome, ProbeOutcome::Busy | ProbeOutcome::LocalOnly)
        {
            let ledger = Ledger::open(repo.clone(), ledger.clone(), ctx.clock.clone());
            let plan = SyncPlan {
                remote: &cfg.sync.remote,
                base: short(&base),
                ledger_branch: ledger_branch.map(short),
            };
            sync(&ledger, &plan, &mut out.data)?;
        }
        let signals = Signals {
            diverged: out.data.base_sync == "diverged",
            ledger_conflict: false,
            base_blocked: out.data.base_sync == "skipped-local-changes",
        };
        let has_remote = done.outcome != ProbeOutcome::LocalOnly;
        Ok(with_freshness(
            out,
            &done.state,
            has_remote,
            signals,
            now,
            &cfg.sync,
        ))
    }
}

/// `--background`: start a detached refresh and report it at once; never waits on the network.
fn background(
    repo: &Repo,
    root: &std::path::Path,
    cfg: &FrobConfig,
    now: i64,
) -> Payload<RefreshReport> {
    let state = RefreshState::load(repo.common_dir());
    let has_remote = repo.remote_url(&cfg.sync.remote).is_some();
    let started = has_remote
        && !frob_ledger::sync_policy::sync_disabled(|k| std::env::var(k).ok())
        && std::env::current_exe().is_ok_and(|exe| {
            match frob_ledger::sync_policy::spawn_refresh(&exe, root) {
                Ok(pid) => {
                    tracing::info!(pid, "refresh --background started");
                    true
                }
                Err(e) => {
                    tracing::warn!(error = %e, "cannot start the background refresh");
                    false
                }
            }
        });
    let outcome = if started { "background" } else { "skipped" };
    let status = if has_remote {
        state.status_line(now, cfg.sync.ttl_secs)
    } else {
        "frob:local-only".to_owned()
    };
    render(report(&state, status, outcome, false))
}

/// Which remote and branches one sync touches.
struct SyncPlan<'a> {
    remote: &'a str,
    base: &'a str,
    ledger_branch: Option<&'a str>,
}

/// `main` for both `main` and `refs/heads/main`.
fn short(name: &str) -> &str {
    name.strip_prefix("refs/heads/").unwrap_or(name)
}

/// The tracking ref a fetch of `branch` fills.
fn tracking(remote: &str, branch: &str) -> String {
    format!("refs/remotes/{remote}/{branch}")
}

/// The refspec that fetches only `branch` into its tracking ref.
fn refspec(remote: &str, branch: &str) -> String {
    format!("+refs/heads/{branch}:{}", tracking(remote, branch))
}

/// A retryable refusal.
fn retry(code: &str, msg: String) -> CliError {
    Refusal::new(code, RefusalClass::GuardRetryByWaiting, msg).into()
}

/// A git failure (spawn, ref, object) as an internal-looking domain refusal.
fn git_err(e: &impl std::fmt::Display) -> CliError {
    Refusal::new("E-SYNC-GIT", RefusalClass::DomainNegative, e.to_string()).into()
}

/// Map a failed fetch or push to the retryable refusal that names why.
fn run_refusal(what: &str, run: &RemoteRun) -> Option<CliError> {
    match run {
        RemoteRun::Done => None,
        RemoteRun::TimedOut => Some(retry(
            "W-SYNC-TIMEOUT",
            format!("{what} timed out after {}s", FETCH_TIMEOUT.as_secs()),
        )),
        RemoteRun::Rejected(t) => Some(retry(
            "W-SYNC-RACE",
            format!(
                "{what} lost a race with another writer; run refresh again: {}",
                t.trim()
            ),
        )),
        RemoteRun::Failed { text, .. } => {
            let lower = text.to_lowercase();
            let code = if [
                "authentication",
                "permission denied",
                "could not read username",
            ]
            .iter()
            .any(|m| lower.contains(m))
            {
                "W-SYNC-AUTH"
            } else {
                "W-SYNC-OFFLINE"
            };
            Some(retry(code, format!("{what} failed: {}", text.trim())))
        }
    }
}

/// Fetch one branch; `Ok(false)` when the remote has no such branch.
fn fetch_branch(repo: &Repo, plan: &SyncPlan<'_>, branch: &str) -> Result<bool, CliError> {
    let run = repo
        .fetch_refs(plan.remote, &[refspec(plan.remote, branch)], FETCH_TIMEOUT)
        .map_err(|e| git_err(&e))?;
    if let RemoteRun::Failed { text, .. } = &run
        && text.contains("couldn't find remote ref")
    {
        tracing::info!(branch, "remote has no such branch yet");
        return Ok(false);
    }
    match run_refusal(&format!("fetch of {branch}"), &run) {
        Some(e) => Err(e),
        None => Ok(true),
    }
}

/// Fetch, integrate, publish and fast-forward, filling `rep`; a conflict is the only refusal that needs action.
// frob:ticket 01M5CW049SPSRGGP5ENQD7BPB3
fn sync(ledger: &Ledger, plan: &SyncPlan<'_>, rep: &mut RefreshReport) -> Result<(), CliError> {
    let repo = ledger.repo();
    let Some(_lock) = RefreshLock::try_acquire(repo.common_dir()).map_err(|e| git_err(&e))? else {
        tracing::info!("another refresh holds the lock; sync skipped");
        return Ok(());
    };
    fetch_branch(repo, plan, plan.base)?;
    let mut conflicts = Vec::new();
    if let Some(branch) = plan.ledger_branch {
        sync_ledger(ledger, plan, branch, rep, &mut conflicts)?;
    }
    rep.base_sync = fast_forward_base(repo, plan);
    // frob:ticket 01M5CW0609NX9MJ45G2R4CQE0R
    // A squash or rebase merge on the host leaves only a trailer; record it as a land.
    match frob_land::hostland::record_host_lands(
        ledger,
        plan.base,
        &tracking(plan.remote, plan.base),
    ) {
        Ok(lands) => tracing::info!(count = lands.len(), "host lands recorded"),
        Err(e) => tracing::warn!(error = %e, "host land detection failed"),
    }
    tracing::info!(ledger = %rep.ledger, pushed = rep.pushed, base = %rep.base_sync, "refresh sync done");
    if conflicts.is_empty() {
        return Ok(());
    }
    rep.conflicts = conflicts.iter().map(|(p, _)| p.clone()).collect();
    let list = conflicts
        .iter()
        .map(|(p, why)| format!("{p}: {why}"))
        .collect::<Vec<_>>()
        .join("; ");
    Err(Refusal::new(
        "E-SYNC-CONFLICT",
        RefusalClass::DomainNegative,
        format!("the ledger cannot be united automatically ({list})"),
    )
    .with_remedy("resolve the listed ledger paths on the remote or locally, then run frob refresh")
    .into())
}

/// Integrate the fetched ledger branch and publish the result, retrying on lost races.
fn sync_ledger(
    ledger: &Ledger,
    plan: &SyncPlan<'_>,
    branch: &str,
    rep: &mut RefreshReport,
    conflicts: &mut Vec<(String, String)>,
) -> Result<(), CliError> {
    let repo = ledger.repo();
    let ours_ref = format!("refs/heads/{branch}");
    let theirs_ref = tracking(plan.remote, branch);
    let mut has_remote = fetch_branch(repo, plan, branch)?;
    "unchanged".clone_into(&mut rep.ledger);
    for attempt in 1..=SYNC_ATTEMPTS {
        if has_remote {
            match ledger.integrate(&ours_ref, &theirs_ref) {
                Ok(Integration::Unchanged) => {}
                Ok(Integration::Created(_)) => "created".clone_into(&mut rep.ledger),
                Ok(Integration::FastForward(_)) => "fast-forward".clone_into(&mut rep.ledger),
                Ok(Integration::Merged { .. }) => "merged".clone_into(&mut rep.ledger),
                Ok(Integration::Conflicts(c)) => {
                    "conflict".clone_into(&mut rep.ledger);
                    conflicts.extend(c.into_iter().map(|c| (c.path, c.reason)));
                    return Ok(());
                }
                Err(e) => return Err(git_err(&e)),
            }
        }
        let Ok(local) = repo.rev_parse(&ours_ref) else {
            return Ok(());
        };
        let remote_tip = repo.rev_parse(&theirs_ref).ok().filter(|_| has_remote);
        if remote_tip == Some(local) {
            return Ok(());
        }
        let expected = remote_tip.map(|o| o.to_string());
        let run = repo
            .push_cas(
                plan.remote,
                &ours_ref,
                &ours_ref,
                expected.as_deref(),
                FETCH_TIMEOUT,
            )
            .map_err(|e| git_err(&e))?;
        if let RemoteRun::Rejected(_) = run
            && attempt < SYNC_ATTEMPTS
        {
            tracing::warn!(
                attempt,
                "ledger push lost the race; fetching and integrating again"
            );
            has_remote = fetch_branch(repo, plan, branch)?;
            continue;
        }
        if let Some(e) = run_refusal("push of the ledger", &run) {
            return Err(e);
        }
        rep.pushed = true;
        return Ok(());
    }
    Ok(())
}

/// Fast-forward the local base to its fetched tracking ref when nothing could be lost.
fn fast_forward_base(repo: &Repo, plan: &SyncPlan<'_>) -> String {
    use frob_land::LandLock;
    let local_ref = format!("refs/heads/{}", plan.base);
    let theirs_ref = tracking(plan.remote, plan.base);
    let (Ok(local), Ok(theirs)) = (repo.rev_parse(&local_ref), repo.rev_parse(&theirs_ref)) else {
        return "none".to_owned();
    };
    if local == theirs {
        return "up-to-date".to_owned();
    }
    let Ok(Some(mb)) = repo.merge_base(&local.to_string(), &theirs.to_string()) else {
        return "diverged".to_owned();
    };
    if mb == theirs {
        return "ahead".to_owned();
    }
    if mb != local {
        return "diverged".to_owned();
    }
    let _land = match LandLock::acquire(repo.common_dir(), Duration::ZERO, "refresh") {
        Ok(l) => l,
        Err(e) => {
            tracing::info!(error = %e, "a land holds the lock; base not moved");
            return "skipped-landing".to_owned();
        }
    };
    let checked_out = repo.list_worktrees().ok().and_then(|w| {
        w.into_iter()
            .find(|w| w.branch.as_deref() == Some(plan.base))
    });
    let moved = match checked_out {
        Some(w) => match repo.merge_branch(&w.path, &theirs_ref) {
            Ok(MergeOutcome::FastForward | MergeOutcome::UpToDate) => Ok(()),
            Ok(other) => Err(format!("unexpected merge result {other:?}")),
            Err(e) => Err(e.to_string()),
        },
        None => repo
            .update_ref_cas(
                &local_ref,
                Some(local),
                theirs,
                "frob refresh: fast-forward base",
            )
            .map_err(|e| e.to_string()),
    };
    match moved {
        Ok(()) => {
            tracing::info!(base = plan.base, to = %theirs, "base fast-forwarded");
            "fast-forwarded".to_owned()
        }
        Err(why) => {
            tracing::warn!(base = plan.base, %why, "base not fast-forwarded");
            "skipped-local-changes".to_owned()
        }
    }
}

/// Build the report from a state and a rendered status line.
fn report(state: &RefreshState, status: String, outcome: &str, changed: bool) -> RefreshReport {
    RefreshReport {
        status,
        class: format!("{:?}", state.class).to_lowercase(),
        outcome: outcome.to_owned(),
        changed,
        remote: state.remote.clone(),
        base: state.base.clone(),
        detail: state.detail.clone(),
        ledger: "none".to_owned(),
        pushed: false,
        base_sync: "none".to_owned(),
        conflicts: Vec::new(),
        age_secs: None,
        freshness: FreshState::Unknown,
        notices: Vec::new(),
    }
}

/// Fill the freshness fields of `out` from the cache at `now` and put the ranked notices in its warnings.
fn with_freshness(
    mut out: Payload<RefreshReport>,
    state: &RefreshState,
    has_remote: bool,
    signals: Signals,
    now: i64,
    sync: &frob_ledger::config::SyncTable,
) -> Payload<RefreshReport> {
    let fresh = assess(state, has_remote, signals, now, Thresholds::from_sync(sync));
    out.warnings.extend(fresh.messages());
    out.data.age_secs = fresh.age_secs;
    out.data.freshness = fresh.state;
    out.data.notices = fresh.notices;
    out
}

/// The payload whose rendered text is the one status line.
fn render(r: RefreshReport) -> Payload<RefreshReport> {
    let text = r.status.clone();
    Payload::new(r).with_rendered(vec![text])
}

/// Map a probe result to the exit contract: 0 ok, 3 retryable, 1 needs action.
fn finish(done: &ProbeReport, now: i64, ttl: u32) -> CliOutcome<RefreshReport> {
    let (name, changed) = match &done.outcome {
        ProbeOutcome::Probed { changed } => ("probed", *changed),
        ProbeOutcome::Cached => ("cached", false),
        ProbeOutcome::Busy => ("busy", false),
        ProbeOutcome::LocalOnly => ("local-only", false),
    };
    let status = if done.outcome == ProbeOutcome::LocalOnly {
        "frob:local-only".to_owned()
    } else {
        done.state.status_line(now, ttl)
    };
    let mut rep = report(&done.state, status, name, changed);
    if done.outcome == ProbeOutcome::LocalOnly {
        "local-only".clone_into(&mut rep.class);
    }
    let Some(code) = done.state.class.code() else {
        return Ok(render(rep));
    };
    if done.outcome == ProbeOutcome::Busy {
        return Ok(render(rep));
    }
    let class = if done.state.class == ProbeClass::NoBase {
        RefusalClass::DomainNegative
    } else {
        RefusalClass::GuardRetryByWaiting
    };
    let message = format!("{}: {}", rep.status, rep.detail);
    let refusal = Refusal::new(code, class, message);
    let refusal = match done.state.class {
        ProbeClass::Auth => refusal.with_remedy("run git fetch origin to re-authenticate"),
        ProbeClass::NoBase => {
            refusal.with_remedy("set [tickets] ref to a branch the remote has, or push it")
        }
        _ => refusal,
    };
    Err(refusal.into())
}

/// Register the `refresh` verb.
pub(crate) fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<Refresh>()
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M5CW046DKVK5QSJR8TMEN0F2
    fn done(class: ProbeClass, outcome: ProbeOutcome) -> ProbeReport {
        ProbeReport {
            outcome,
            state: RefreshState {
                class,
                probed_at: 100,
                ..RefreshState::default()
            },
        }
    }

    fn exit_of(r: &CliOutcome<RefreshReport>) -> Option<(String, RefusalClass)> {
        match r {
            Err(CliError::Refusal(x)) => Some((x.code.clone(), x.class)),
            _ => None,
        }
    }

    #[test]
    fn ok_and_busy_and_local_only_exit_zero() {
        assert!(
            finish(
                &done(ProbeClass::Ok, ProbeOutcome::Probed { changed: true }),
                100,
                300
            )
            .is_ok()
        );
        assert!(finish(&done(ProbeClass::Offline, ProbeOutcome::Busy), 100, 300).is_ok());
        let lo = finish(
            &done(ProbeClass::Unknown, ProbeOutcome::LocalOnly),
            100,
            300,
        )
        .expect("ok");
        assert_eq!(lo.data.status, "frob:local-only");
        assert_eq!(lo.data.class, "local-only");
    }

    #[test]
    fn retryable_classes_exit_three_and_no_base_exits_one() {
        for (c, code) in [
            (ProbeClass::Offline, "W-SYNC-OFFLINE"),
            (ProbeClass::Timeout, "W-SYNC-TIMEOUT"),
            (ProbeClass::Auth, "W-SYNC-AUTH"),
            (ProbeClass::Rate, "W-SYNC-RATE"),
        ] {
            let r = finish(&done(c, ProbeOutcome::Probed { changed: false }), 100, 300);
            assert_eq!(
                exit_of(&r),
                Some((code.to_owned(), RefusalClass::GuardRetryByWaiting))
            );
        }
        let r = finish(
            &done(ProbeClass::NoBase, ProbeOutcome::Probed { changed: false }),
            100,
            300,
        );
        assert_eq!(
            exit_of(&r),
            Some(("E-SYNC-NO-BASE".to_owned(), RefusalClass::DomainNegative))
        );
    }
}
