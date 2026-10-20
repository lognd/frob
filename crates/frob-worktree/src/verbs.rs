//! The CLI verbs: `work [--here]` and `requeue`; `start` stays as a hidden alias of `work --here`.

use gob_path::Shown;
use std::path::PathBuf;

use frob_lease::{Holder, Lease, LeaseStore};
use frob_ledger::{Ledger, TicketId};
use frob_pm::PmConfig;
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_git::Repo;
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::{WorktreeConfig, ledger_config};
use crate::error::WorktreeError;
use crate::gc::{GcConfig, Mode, glue};
use crate::work::{Requeued, Started, WorkOptions, Workspace};

/// The opened pieces a verb needs.
struct Opened {
    sprint_gate: bool,
    ledger: Ledger,
    leases: LeaseStore,
    config: WorktreeConfig,
    gc: GcConfig,
}

impl Opened {
    /// Open ledger, lease store and worktree settings for the repository containing `ctx.cwd`.
    fn new(ctx: &Context) -> Result<Self, WorktreeError> {
        let repo = Repo::discover(&ctx.cwd).map_err(|e| WorktreeError::Config(e.to_string()))?;
        let root = repo
            .work_dir()
            .map(std::path::Path::to_path_buf)
            .ok_or_else(|| {
                WorktreeError::Config(format!(
                    "{} is not inside a git work tree",
                    Shown::of(&ctx.cwd)
                ))
            })?;
        let ledger_cfg = ledger_config(&root).map_err(WorktreeError::Config)?;
        // frob:ticket 01M5CY4615SPGHB682NX2S3S24
        frob_ledger::branch::ensure_for_config(&repo, &ledger_cfg)
            .map_err(|e| WorktreeError::Config(e.to_string()))?;
        let config =
            WorktreeConfig::load(&root).map_err(|e| WorktreeError::Config(e.to_string()))?;
        let gc = GcConfig::load(&root).map_err(|e| WorktreeError::Config(e.to_string()))?;
        // frob:ticket 01M4GWKEMB266C6GTFEP4R3G7W
        let pm = PmConfig::load_repo_wide(&root, &ledger_cfg.ref_name)
            .map_err(|e| WorktreeError::Config(e.to_string()))?;
        let wip = pm.wip;
        let (leases, _) = frob_lease::open_store_from_file(&root, ctx.clock.clone())?;
        Ok(Self {
            sprint_gate: pm.pm.sprint_gate,
            ledger: Ledger::open(repo, ledger_cfg, ctx.clock.clone()),
            leases: leases
                .with_holder_limit(wip.in_progress_per_identity)
                .with_repo_limit(wip.in_progress)
                .with_expedite_max(pm.classes.expedite_max),
            config,
            gc,
        })
    }

    /// The throttled garbage-collection pass before `work` builds anything; its problems are warnings, never errors.
    // frob:ticket 01M424QEMYGC9VZZYX9BZXZK29
    fn collect_garbage(&self) -> Vec<String> {
        let report = glue::run_for(
            &self.ledger,
            &self.leases,
            &self.config,
            &self.gc,
            Mode::Auto,
        );
        glue::notices(&report)
    }

    /// `opts` with the sprint gate set from `[pm] sprint_gate`.
    fn gated(&self, opts: &WorkOptions) -> WorkOptions {
        WorkOptions {
            sprint_gate: self.sprint_gate,
            ..opts.clone()
        }
    }

    fn workspace(&self) -> Workspace<'_> {
        Workspace {
            ledger: &self.ledger,
            leases: &self.leases,
            config: &self.config,
        }
    }
}

/// Output of `work` and `start`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct StartData {
    /// Full ULID.
    pub id: TicketId,
    /// Handle with `~`.
    pub handle: String,
    /// The holder's worktree.
    pub path: PathBuf,
    /// The branch checked out there (`work` only).
    pub branch: Option<String>,
    /// The lease in force.
    pub lease: Lease,
    /// True when this call created the worktree.
    pub created_worktree: bool,
    /// How merging the base went.
    pub merge: Option<String>,
    /// Paths left conflicted by the base merge.
    pub conflicts: Vec<String>,
    /// The previous holder when the lease was stolen.
    pub stolen_from: Option<Holder>,
}

/// The payload carrying `already` and the warnings of a start.
fn start_payload(s: Started) -> Payload<StartData> {
    let already = s.already;
    let warnings = s.warnings.clone();
    let mut p = Payload::new(StartData {
        id: s.id,
        handle: s.handle,
        path: s.path,
        branch: s.branch,
        lease: s.lease,
        created_worktree: s.created_worktree,
        merge: s.merge,
        conflicts: s.conflicts,
        stolen_from: s.stolen_from,
    })
    .with_already(already);
    for w in warnings {
        p = p.with_warning(w);
    }
    p
}

/// The positional ticket every worktree verb takes.
#[derive(Debug, Clone, clap::Args)]
struct TicketArg {
    #[arg(
        value_name = "TICKET",
        help = "Full ULID, ~handle or alias of the ticket"
    )]
    ticket: String,
}

/// The reason of `--steal` and `--unplanned`: one `--reason` serves whichever flags are set, and it is required by both and meaningless alone.
fn flag_reasons(
    steal: bool,
    unplanned: bool,
    reason: Option<String>,
) -> Result<(Option<String>, Option<String>), CliError> {
    match (steal || unplanned, reason) {
        (true, Some(r)) if !r.trim().is_empty() => {
            Ok((steal.then(|| r.clone()), unplanned.then_some(r)))
        }
        (true, _) => Err(CliError::Usage(
            "--steal and --unplanned need a non-empty --reason".into(),
        )),
        (false, Some(_)) => Err(CliError::Usage(
            "--reason is only used with --steal or --unplanned".into(),
        )),
        (false, None) => Ok((None, None)),
    }
}

/// The flags of `work`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct WorkArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(
        long,
        value_name = "PATH",
        help = "Create the worktree here instead of under [worktree] dir"
    )]
    worktree: Option<PathBuf>,
    #[arg(
        long,
        conflicts_with = "worktree",
        help = "Lease the ticket for this checkout: no new worktree or branch"
    )]
    here: bool,
    #[arg(
        long,
        value_name = "SECS",
        help = "Queue fairly for a blocked scope for up to SECS seconds instead of refusing"
    )]
    wait: Option<u64>,
    #[arg(long, help = "Take over a lease held by someone else (needs --reason)")]
    steal: bool,
    #[arg(
        long,
        help = "Start a ticket outside the active cycle: it joins the cycle as an over-commit (needs --reason)"
    )]
    unplanned: bool,
    #[arg(
        long,
        value_name = "TEXT",
        help = "Why the lease is stale (with --steal) or why the work is unplanned (with --unplanned)"
    )]
    reason: Option<String>,
}

/// The flags of `start`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct StartArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(long, help = "Take over a lease held by someone else (needs --reason)")]
    steal: bool,
    #[arg(
        long,
        value_name = "TEXT",
        help = "Why the lease is stale (with --steal)"
    )]
    reason: Option<String>,
}

/// The flags of `requeue`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct RequeueArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(
        long,
        value_name = "TEXT",
        required = true,
        help = "Why the ticket goes back to todo"
    )]
    reason: String,
}

/// Lease a ticket, create its worktree and branch, and move it to in-progress; `--here` leases it for this checkout instead.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "work",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Work {
    ticket: String,
    opts: WorkOptions,
    here: bool,
}

impl Command for Work {
    type Data = StartData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<WorkArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<WorkArgs>(m)?;
        let (steal, unplanned) = flag_reasons(a.steal, a.unplanned, a.reason)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            opts: WorkOptions {
                worktree: a.worktree,
                steal,
                unplanned,
                wait_secs: a.wait.unwrap_or(0),
                sprint_gate: false,
            },
            here: a.here,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<StartData> {
        let opened = Opened::new(ctx)?;
        if self.here {
            tracing::debug!(ticket = %self.ticket, "work --here: leasing for this checkout");
            return start_here(&opened, ctx, &self.ticket, &self.opts);
        }
        let notices = opened.collect_garbage();
        let started = opened
            .workspace()
            .work(&self.ticket, &opened.gated(&self.opts))?;
        Ok(notices
            .into_iter()
            .fold(start_payload(started), Payload::with_warning))
    }
}

/// Deprecated alias of `work --here`, removed in the next minor release.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "start",
    product = "frob",
    deprecated = "work --here",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Start {
    ticket: String,
    opts: WorkOptions,
}

impl Command for Start {
    type Data = StartData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<StartArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<StartArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            opts: WorkOptions {
                steal: flag_reasons(a.steal, false, a.reason)?.0,
                ..WorkOptions::default()
            },
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<StartData> {
        let opened = Opened::new(ctx)?;
        start_here(&opened, ctx, &self.ticket, &self.opts)
    }
}

/// Lease `ticket` for the current checkout and move it to in-progress (`work --here`).
fn start_here(
    opened: &Opened,
    ctx: &Context,
    ticket: &str,
    opts: &WorkOptions,
) -> Outcome<StartData> {
    let cwd = opened
        .ledger
        .repo()
        .work_dir()
        .map_or_else(|| ctx.cwd.clone(), std::path::Path::to_path_buf);
    let started = opened
        .workspace()
        .start_with(ticket, &cwd, &opened.gated(opts))?;
    Ok(start_payload(started))
}

/// Output of `requeue`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct RequeueData {
    /// Full ULID.
    pub id: TicketId,
    /// Handle with `~`.
    pub handle: String,
    /// The lease that was released, if any.
    pub released: Option<Lease>,
}

impl From<&Requeued> for RequeueData {
    fn from(r: &Requeued) -> Self {
        Self {
            id: r.id,
            handle: r.handle.clone(),
            released: r.released.clone(),
        }
    }
}

/// Release a ticket's lease and move it back to todo.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "requeue",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Requeue {
    ticket: String,
    reason: String,
}

impl Command for Requeue {
    type Data = RequeueData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<RequeueArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<RequeueArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            reason: a.reason,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<RequeueData> {
        let opened = Opened::new(ctx)?;
        let done = opened.workspace().requeue(&self.ticket, &self.reason)?;
        Ok(Payload::new(RequeueData::from(&done)).with_already(done.already))
    }
}
