//! `frob claim notices [--ack]`: list the idle-window notices of live claims, or acknowledge the caller's own.
//!
//! Reads only this clone's observations and the lease store (`distributed-tickets.md` section 4.4).

// frob:ticket 01M6Q1JHTF77GRJRN0BDE3BN99

use frob_worktree::next::EvictPolicy;
use frob_worktree::{Workspace, claim_notice::ClaimNotice};
use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::FrobConfig;
use crate::ticket::open;
use crate::workspace::{Located, config_refusal};

/// One live claim's idle state as `claim notices` reports it.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct NoticeRow {
    /// Handle of the claimed ticket.
    pub handle: String,
    /// True when the caller holds the claim.
    pub mine: bool,
    /// Idle rank this clone observes (0 is quiet).
    pub rank: usize,
    /// The rank the holder acknowledged, if any.
    pub acked_rank: Option<usize>,
    /// The line the caller should see for this claim, absent when there is none.
    pub line: Option<String>,
}

/// Output of `claim notices`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct NoticesData {
    /// Every live in-progress claim; empty after `--ack`.
    pub notices: Vec<NoticeRow>,
    /// Handles acknowledged by `--ack`; empty when listing.
    pub acked: Vec<String>,
}

/// The `--ack` flag of `claim notices`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct NoticesArgs {
    #[arg(
        long,
        help = "Acknowledge the current idle notice of every claim you hold, silencing it until the next threshold"
    )]
    ack: bool,
}

/// List the idle notices of live claims, or acknowledge the caller's own with `--ack`.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "claim notices",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct ClaimNotices {
    ack: bool,
}

impl Command for ClaimNotices {
    type Data = NoticesData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<NoticesArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<NoticesArgs>(m)?;
        Ok(Self { ack: a.ack })
    }

    fn run(&self, ctx: &Context) -> Outcome<NoticesData> {
        let ledger = open(ctx)?;
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
        let (leases, _) = crate::ticket::open_lease_store(ctx)?;
        let now = ctx.clock.now();
        let policy = EvictPolicy {
            windows: cfg.claims,
            utc_offset_secs: gob_time::Shown::local_offset_secs(now),
            in_ci: std::env::var_os("CI").is_some_and(|v| !v.is_empty()),
        };
        let ws = Workspace {
            ledger: &ledger,
            leases: &leases,
            config: &cfg.worktree,
        };
        if self.ack {
            let acked = ws.ack_claim_notices(&policy)?;
            tracing::info!(acked = acked.len(), "claim notices acknowledged");
            return Ok(Payload::new(NoticesData {
                notices: Vec::new(),
                acked,
            })
            .with_already(false));
        }
        let notices = ws.claim_idle_notices(&policy)?;
        tracing::info!(claims = notices.len(), "claim notices listed");
        Ok(Payload::new(NoticesData {
            notices: notices.iter().map(row).collect(),
            acked: Vec::new(),
        }))
    }
}

/// The report row of one notice.
fn row(n: &ClaimNotice) -> NoticeRow {
    NoticeRow {
        handle: n.handle.clone(),
        mine: n.mine,
        rank: n.status.rank(),
        acked_rank: n.acked_rank,
        line: n.line().map(str::to_owned),
    }
}
