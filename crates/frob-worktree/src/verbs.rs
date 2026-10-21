//! The CLI verbs: `work [--here]` and `requeue`; `start` stays as a hidden alias of `work --here`.

use gob_path::Shown;
use std::io::{BufRead, IsTerminal, Write};
use std::path::PathBuf;

use frob_lease::{Holder, Lease, LeaseStore};
use frob_ledger::{Ledger, TicketId};
use frob_pm::PmConfig;
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_git::Repo;
use schemars::JsonSchema;
use serde::Serialize;

use crate::anyway::{Anyway, DEFAULT_EXPIRY_DAYS};
use crate::config::{WorktreeConfig, ledger_config};
use crate::error::WorktreeError;
use crate::gc::{GcConfig, Mode, glue};
use crate::next::EvictPolicy;
use crate::work::{Requeued, Started, WorkOptions, Workspace};
use frob_ledger::claim_window::{ClaimWindows, ClaimsClassTable, ClaimsTable};

/// The opened pieces a verb needs.
struct Opened {
    sprint_gate: bool,
    ledger: Ledger,
    leases: LeaseStore,
    config: WorktreeConfig,
    gc: GcConfig,
    /// Root of the primary checkout, where `frob.toml` lives.
    root: PathBuf,
}

/// Load the `[claims]` and `[claims.class]` tables into the window rules; `Err` carries why they cannot be read.
// frob:ticket 01M5E1MXMVSDYCE9SZYAJEBGZG
fn claim_windows(root: &std::path::Path) -> Result<ClaimWindows, String> {
    let tables = gob_config::ConfigDocument::read(root, "frob").and_then(|doc| {
        Ok((
            doc.table::<ClaimsTable>()?.value,
            doc.table::<ClaimsClassTable>()?.value,
        ))
    });
    match tables {
        Ok((claims, class)) => ClaimWindows::from_tables(&claims, &class),
        Err(e) => Err(e.to_string()),
    }
}

/// Load the `[claims]` tables, with the local zone offset at `now`, into the policy `work --next` evicts by; `None` when they cannot be loaded.
// frob:ticket 01M5DWZYEFXGXNRQ4KH8DKB004
fn evict_policy(root: &std::path::Path, in_ci: bool, now: gob_time::Stamp) -> Option<EvictPolicy> {
    match claim_windows(root) {
        Ok(windows) => {
            tracing::debug!(in_ci, "work --next: eviction policy loaded");
            Some(EvictPolicy {
                windows,
                utc_offset_secs: gob_time::Shown::local_offset_secs(now),
                in_ci,
            })
        }
        Err(why) => {
            tracing::warn!(%why, "work --next: [claims] unreadable; eviction disabled");
            None
        }
    }
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
            root,
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
    let rows = crate::work_view::work_rows(&p.data, already);
    p = p.with_rendered(rows);
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

/// The `--reason` of each flag that needs one: the stolen-lease, unplanned and anyway reasons.
type Reasons = (Option<String>, Option<String>, Option<String>);

/// The reason of `--steal`, `--unplanned` and `--anyway`: one `--reason` serves whichever flags are set, and it is required by each and meaningless alone.
fn flag_reasons(
    steal: bool,
    unplanned: bool,
    anyway: bool,
    reason: Option<String>,
) -> Result<Reasons, CliError> {
    match (steal || unplanned || anyway, reason) {
        (true, Some(r)) if !r.trim().is_empty() => Ok((
            steal.then(|| r.clone()),
            unplanned.then(|| r.clone()),
            anyway.then_some(r),
        )),
        (true, _) => Err(CliError::Usage(
            "--steal, --unplanned and --anyway need a non-empty --reason".into(),
        )),
        (false, Some(_)) => Err(CliError::Usage(
            "--reason is only used with --steal, --unplanned or --anyway".into(),
        )),
        (false, None) => Ok((None, None, None)),
    }
}

/// The flags of `work`, declared once.
#[allow(clippy::struct_excessive_bools)] // one bool per CLI flag
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct WorkArgs {
    #[arg(
        value_name = "TICKET",
        required_unless_present = "next",
        conflicts_with = "next",
        help = "Full ULID, ~handle or alias of the ticket"
    )]
    ticket: Option<String>,
    #[arg(
        long,
        conflicts_with = "here",
        help = "Claim the best doable ticket instead of naming one, retrying when another clone wins the race"
    )]
    next: bool,
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
        help = "Why the lease is stale (--steal), the work is unplanned (--unplanned) or the claim is worked over (--anyway)"
    )]
    reason: Option<String>,
    #[arg(
        long,
        help = "Work on a ticket another clone has claimed, without taking the claim (needs --reason)"
    )]
    anyway: bool,
    #[arg(
        long = "anyway-scope",
        value_name = "GLOB",
        requires = "anyway",
        help = "Limit the --anyway work to these globs instead of the ticket's scope (repeatable)"
    )]
    anyway_scope: Vec<String>,
    #[arg(
        long = "anyway-days",
        value_name = "N",
        requires = "anyway",
        help = "Days until the --anyway escape expires (default 7)"
    )]
    anyway_days: Option<u32>,
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
    ticket: Option<String>,
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
        let (steal, unplanned, anyway) = flag_reasons(a.steal, a.unplanned, a.anyway, a.reason)?;
        let anyway = anyway.map(|reason| Anyway {
            reason,
            scope: a.anyway_scope,
            expiry_days: a.anyway_days.unwrap_or(DEFAULT_EXPIRY_DAYS),
        });
        Ok(Self {
            ticket: a.ticket,
            opts: WorkOptions {
                worktree: a.worktree,
                steal,
                unplanned,
                wait_secs: a.wait.unwrap_or(0),
                sprint_gate: false,
                anyway,
            },
            here: a.here,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<StartData> {
        let opened = Opened::new(ctx)?;
        let Some(ticket) = &self.ticket else {
            // frob:ticket 01M5CW05BZQR83F5SJTQEH8MRN
            let notices = opened.collect_garbage();
            let in_ci = std::env::var_os("CI").is_some_and(|v| !v.is_empty());
            let policy = evict_policy(&opened.root, in_ci, opened.ledger.clock().now());
            let started = opened.workspace().work_next_evicting(
                &opened.gated(&self.opts),
                crate::next::MAX_ATTEMPTS,
                policy.as_ref(),
            )?;
            return Ok(notices
                .into_iter()
                .fold(start_payload(started), Payload::with_warning));
        };
        if self.here {
            tracing::debug!(ticket = %ticket, "work --here: leasing for this checkout");
            return start_here(&opened, ctx, ticket, &self.opts);
        }
        let notices = opened.collect_garbage();
        let started = opened.workspace().work(ticket, &opened.gated(&self.opts))?;
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
                steal: flag_reasons(a.steal, false, false, a.reason)?.0,
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

/// Output of `claim restore`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct RestoreData {
    /// Full ULID.
    pub id: TicketId,
    /// Handle with `~`.
    pub handle: String,
    /// The parked branch the work came from.
    pub parked: String,
    /// The restored `ticket/<handle>` tip.
    pub tip: String,
}

/// Put an evicted claim's parked work back as its `ticket/<handle>` branch; anyone may, until someone else claims.
// frob:ticket 01M5DN9Q57S88B7DQQH8BAXZ01
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "claim restore",
    product = "frob",
    idempotent = false,
    exits(ok, refused, usage, internal)
)]
pub struct ClaimRestore {
    ticket: String,
    reason: String,
}

impl Command for ClaimRestore {
    type Data = RestoreData;

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

    fn run(&self, ctx: &Context) -> Outcome<RestoreData> {
        let opened = Opened::new(ctx)?;
        let r = opened
            .workspace()
            .restore_claim(&self.ticket, &self.reason)?;
        Ok(Payload::new(RestoreData {
            id: r.id,
            handle: r.handle,
            parked: r.parked,
            tip: r.tip,
        }))
    }
}

/// The flags of `claim evict`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct EvictArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(
        long,
        value_name = "TEXT",
        required = true,
        help = "Why the claim is being evicted"
    )]
    reason: String,
    #[arg(
        long,
        help = "Confirm a repeat eviction of the same holder inside the flap window"
    )]
    yes: bool,
}

/// Output of `claim evict`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct EvictData {
    /// Full ULID.
    pub id: TicketId,
    /// Handle with `~`.
    pub handle: String,
    /// The previous holder.
    pub holder: String,
    /// The parked ref preserving the holder's work.
    pub parked: String,
    /// Idle seconds this clone measured.
    pub idle_secs: u64,
    /// Evictions this actor may still perform today.
    pub rate_left: u32,
    /// True when this repeated an eviction of the same holder inside the flap window.
    pub flagged: bool,
}

/// Evict an idle claim: park the holder's work, free the ticket and report the remaining daily rate.
// frob:ticket 01M5DTGG9XWMEBRA51PA6CYWAE
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "claim evict",
    product = "frob",
    idempotent = false,
    exits(ok, refused, usage, internal)
)]
pub struct ClaimEvict {
    ticket: String,
    reason: String,
    yes: bool,
}

impl Command for ClaimEvict {
    type Data = EvictData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<EvictArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<EvictArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            reason: a.reason,
            yes: a.yes,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<EvictData> {
        let opened = Opened::new(ctx)?;
        let in_ci = std::env::var_os("CI").is_some_and(|v| !v.is_empty());
        let policy =
            evict_policy(&opened.root, in_ci, opened.ledger.clock().now()).ok_or_else(|| {
                WorktreeError::Config("[claims] is unreadable; cannot judge idleness".to_owned())
            })?;
        let yes = self.yes;
        let interactive = std::io::stdin().is_terminal() && std::io::stdout().is_terminal();
        let e = opened.workspace().evict_claim_confirming(
            &self.ticket,
            &self.reason,
            &policy,
            &mut |question| yes || (interactive && prompt_yes(question)),
        )?;
        Ok(Payload::new(EvictData {
            id: e.id,
            handle: e.handle,
            holder: e.holder,
            parked: e.parked,
            idle_secs: e.idle_secs,
            rate_left: e.rate_left,
            flagged: e.flapped,
        }))
    }
}

/// Ask `question` on the terminal and report whether the answer was yes.
// frob:ticket 01M5DZJ99WRFPNK6WS3KZWDC0G
fn prompt_yes(question: &str) -> bool {
    let mut out = std::io::stdout().lock();
    let _ = write!(out, "{question} [y/N] ");
    let _ = out.flush();
    let mut line = String::new();
    std::io::stdin().lock().read_line(&mut line).is_ok() && is_yes(&line)
}

/// True for an affirmative answer line (`y`, `yes`, any case).
// frob:ticket 01M5DZJ99WRFPNK6WS3KZWDC0G
fn is_yes(line: &str) -> bool {
    matches!(line.trim().to_ascii_lowercase().as_str(), "y" | "yes")
}

/// The flags of `claim hold`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct HoldArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(
        long,
        value_name = "DATE",
        required = true,
        help = "Last day of the hold (YYYY-MM-DD, UTC)"
    )]
    until: String,
    #[arg(
        long,
        value_name = "TEXT",
        required = true,
        help = "Why the holder is away"
    )]
    reason: String,
}

/// Output of `claim hold`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct HoldData {
    /// Full ULID.
    pub id: TicketId,
    /// Handle with `~`.
    pub handle: String,
    /// The last day of the hold.
    pub until: String,
    /// Epoch seconds at which the hold ends.
    pub until_secs: i64,
}

/// Stop a claim's idle clock until a date, for a holder who is away.
// frob:ticket 01M5E1MXMVSDYCE9SZYAJEBGZG
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "claim hold",
    product = "frob",
    idempotent = false,
    exits(ok, refused, usage, internal)
)]
pub struct ClaimHold {
    ticket: String,
    until: String,
    reason: String,
}

impl Command for ClaimHold {
    type Data = HoldData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<HoldArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<HoldArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            until: a.until,
            reason: a.reason,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<HoldData> {
        let until: gob_time::Day = self.until.parse().map_err(WorktreeError::Usage)?;
        let opened = Opened::new(ctx)?;
        let windows = claim_windows(&opened.root).map_err(WorktreeError::Config)?;
        let now = opened.ledger.clock().now().unix();
        // No local-zone source is available here; the hold ends at the end of a UTC day.
        let hold =
            opened
                .workspace()
                .hold_claim(&self.ticket, until, &self.reason, now, 0, &windows)?;
        let id = opened
            .ledger
            .resolve(&self.ticket)
            .map_err(WorktreeError::from)?;
        let handle = opened
            .ledger
            .show(id)
            .map_err(WorktreeError::from)?
            .summary
            .handle;
        Ok(Payload::new(HoldData {
            id,
            handle,
            until: until.to_string(),
            until_secs: hold.until,
        }))
    }
}

/// Output of `claim resume`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ResumeData {
    /// Full ULID.
    pub id: TicketId,
    /// Handle with `~`.
    pub handle: String,
    /// True when an active hold was ended; false when there was none.
    pub resumed: bool,
}

/// End a claim hold early; a ticket with no active hold is left alone.
// frob:ticket 01M5E1MXMVSDYCE9SZYAJEBGZG
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "claim resume",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct ClaimResume {
    ticket: String,
}

impl Command for ClaimResume {
    type Data = ResumeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<TicketArg>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<TicketArg>(m)?;
        Ok(Self { ticket: a.ticket })
    }

    fn run(&self, ctx: &Context) -> Outcome<ResumeData> {
        let opened = Opened::new(ctx)?;
        let now = opened.ledger.clock().now().unix();
        let resumed = opened.workspace().resume_claim(&self.ticket, now)?;
        let id = opened
            .ledger
            .resolve(&self.ticket)
            .map_err(WorktreeError::from)?;
        let handle = opened
            .ledger
            .show(id)
            .map_err(WorktreeError::from)?
            .summary
            .handle;
        Ok(Payload::new(ResumeData {
            id,
            handle,
            resumed,
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::{claim_windows, evict_policy, is_yes};

    // frob:ticket 01M5DZJ99WRFPNK6WS3KZWDC0G
    // frob:tests is_yes
    #[test]
    fn is_yes_accepts_y_and_yes_in_any_case_only() {
        assert!(is_yes("y\n"));
        assert!(is_yes(" YES "));
        assert!(!is_yes(""));
        assert!(!is_yes("no"));
    }

    // frob:tests evict_policy
    #[test]
    fn evict_policy_reads_claims_tables_and_carries_ci() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("frob.toml"),
            "[claims]\nevict_agent = \"confirm\"\n",
        )
        .unwrap();
        let p = evict_policy(dir.path(), true, gob_time::Stamp::from_unix(0)).unwrap();
        assert!(p.in_ci);
        assert!(!p.windows.evict_agent_auto());
        let d = tempfile::tempdir().unwrap();
        let p = evict_policy(d.path(), false, gob_time::Stamp::from_unix(0)).unwrap();
        assert!(!p.in_ci);
        assert!(p.windows.evict_agent_auto());
    }

    // frob:tests evict_policy
    #[test]
    fn evict_policy_is_none_for_a_bad_claims_table() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("frob.toml"), "[claims]\nbogus = 1\n").unwrap();
        assert!(evict_policy(dir.path(), false, gob_time::Stamp::from_unix(0)).is_none());
    }

    // frob:tests claim_windows
    #[test]
    fn claim_windows_loads_defaults_and_rejects_a_bad_table() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("frob.toml"),
            "[claims]\nmax_hold_days = 7\n",
        )
        .unwrap();
        assert!(claim_windows(dir.path()).is_ok());
        std::fs::write(dir.path().join("frob.toml"), "[claims]\nbogus = 1\n").unwrap();
        assert!(claim_windows(dir.path()).is_err());
    }
}
