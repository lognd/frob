//! The `land` verb.

use frob_ledger::model::Outcome as TicketOutcome;
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};

use crate::error::LandError;
use crate::land::land;
use crate::lock::LandLock;
use crate::plan::{LandOptions, LandOutcome, RetryPolicy};
use frob_ledger::TicketId;

/// Land a leased ticket branch onto the base branch, close the ticket and clean up.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "land",
    product = "frob",
    idempotent = true,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct Land {
    opts: LandOptions,
}

/// The flags of `land`, declared once; the help text is the operator-facing contract.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
#[allow(clippy::struct_excessive_bools)] // one bool per CLI flag
struct LandArgs {
    #[arg(
        value_name = "TICKET",
        help = "Full ULID, ~handle or alias; defaults to the ticket leased by this worktree"
    )]
    ticket: Option<String>,
    #[arg(long, help = "Push the base branch to origin after landing")]
    push: bool,
    #[arg(
        long,
        value_name = "SECS",
        help = "Wait up to this many seconds for the land lock and to retry when the base moves (default 0)"
    )]
    wait: Option<u64>,
    #[arg(
        long,
        help = "Show who holds the land lock, at which stage and for how long; land nothing"
    )]
    status: bool,
    #[arg(long, help = "Keep the worktree and branch after landing")]
    keep_worktree: bool,
    #[arg(
        long,
        help = "Close without measured evidence; needs --reason and is audited"
    )]
    no_evidence: bool,
    #[arg(
        long,
        value_name = "TEXT",
        help = "Why no evidence or no changelog note is recorded (with --no-evidence or --no-changelog)"
    )]
    reason: Option<String>,
    #[arg(
        long,
        help = "Land despite a red or unreadable base CI; needs --reason and is audited on the ticket"
    )]
    override_base_ci: bool,
    #[arg(
        long,
        help = "Close without a changelog fragment; needs --reason and is audited"
    )]
    no_changelog: bool,
    #[arg(
        long,
        value_name = "VALUE",
        value_parser = gob_cli::clap::builder::PossibleValuesParser::new(TicketOutcome::NAMES),
        help = "Outcome the ticket is closed with (default done)"
    )]
    outcome: Option<String>,
}

impl Command for Land {
    type Data = LandOutcome;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<LandArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<LandArgs>(m)?;
        let outcome = match a.outcome.clone() {
            Some(s) => s
                .parse::<TicketOutcome>()
                .map_err(|e| CliError::Usage(format!("--outcome: {e}")))?,
            None => TicketOutcome::Done,
        };
        if let Some(msg) =
            frob_evidence::done::missing_reason(Some(outcome), a.reason.clone().as_deref())
        {
            return Err(CliError::Usage(msg));
        }
        let reason = a.reason.clone().filter(|r| !r.trim().is_empty());
        let (no_evidence, no_changelog) = (a.no_evidence, a.no_changelog);
        let given = |flag: &str| match &reason {
            Some(r) => Ok(r.clone()),
            None => Err(CliError::Usage(format!(
                "{flag} needs --reason <text> saying why"
            ))),
        };
        let override_base_ci = a
            .override_base_ci
            .then(|| given("--override-base-ci"))
            .transpose()?;
        let claims = frob_evidence::done::guards_apply(Some(outcome));
        if claims
            && !no_evidence
            && !no_changelog
            && override_base_ci.is_none()
            && a.reason.clone().is_some()
        {
            return Err(CliError::Usage(
                "--reason is only used with --no-evidence, --no-changelog, --override-base-ci or an invalid, duplicate or wont-fix outcome".to_owned(),
            ));
        }
        let no_evidence_reason = no_evidence.then(|| given("--no-evidence")).transpose()?;
        let no_changelog_reason = no_changelog.then(|| given("--no-changelog")).transpose()?;
        Ok(Self {
            opts: LandOptions {
                handle: a.ticket,
                dry_run: false,
                push: a.push,
                wait_secs: a.wait.unwrap_or(0),
                keep_worktree: a.keep_worktree,
                no_evidence_reason,
                no_changelog_reason,
                reason: if claims { None } else { reason.clone() },
                outcome,
                retry: RetryPolicy::default(),
                ci_reader: None,
                override_base_ci,
                prechecked: false,
                status: a.status,
            },
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<LandOutcome> {
        let mut opts = self.opts.clone();
        opts.dry_run = ctx.dry_run;
        if opts.status {
            return lock_status(ctx);
        }
        let out = land(&ctx.cwd, &opts, &ctx.clock)?;
        let already = out.already;
        let mut warnings = out.warnings.clone();
        warnings.extend(out.pre_existing.iter().map(|n| {
            format!(
                "pre-existing finding on the base, not blocking: {} {}: {}",
                n.rule,
                n.path.as_deref().unwrap_or("-"),
                n.message
            )
        }));
        warnings.extend(out.resolved.iter().map(|n| {
            format!(
                "resolved finding: {} {}: {}",
                n.rule,
                n.path.as_deref().unwrap_or("-"),
                n.message
            )
        }));
        let mut p = Payload::new(out).with_already(already);
        for w in warnings {
            p = p.with_warning(w);
        }
        Ok(p)
    }
}

/// The `--status` result: the lock state in an otherwise empty outcome.
fn lock_status(ctx: &Context) -> Outcome<LandOutcome> {
    let repo = gob_git::Repo::discover(&ctx.cwd).map_err(|e| LandError::Config(e.to_string()))?;
    let status = LandLock::status(repo.common_dir(), &*ctx.clock)?;
    tracing::info!(held = status.held, summary = %status.summary, "land lock status");
    let nil: TicketId = "0"
        .repeat(26)
        .parse()
        .map_err(|_| LandError::Config("nil id".to_owned()))?;
    let mut out = crate::land::blank_outcome(nil, "-", "-", &LandOptions::default());
    out.lock = Some(status.clone());
    Ok(Payload::new(out).with_warning(status.summary))
}
