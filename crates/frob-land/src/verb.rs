//! The `land` verb.

use frob_ledger::model::Outcome as TicketOutcome;
use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome, Payload};

use crate::land::land;
use crate::plan::{LandOptions, LandOutcome};

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

fn text(m: &ArgMatches, name: &str) -> Option<String> {
    m.get_one::<String>(name).cloned()
}

impl Command for Land {
    type Data = LandOutcome;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("ticket").value_name("TICKET").help(
                "Full ULID, ~handle or alias; defaults to the ticket leased by this worktree",
            ),
        )
        .arg(
            Arg::new("push")
                .long("push")
                .action(ArgAction::SetTrue)
                .help("Push the base branch to origin after landing"),
        )
        .arg(
            Arg::new("wait")
                .long("wait")
                .value_name("SECS")
                .value_parser(gob_cli::clap::value_parser!(u64))
                .help("Wait up to this many seconds for the land lock (default 0)"),
        )
        .arg(
            Arg::new("keep-worktree")
                .long("keep-worktree")
                .action(ArgAction::SetTrue)
                .help("Keep the worktree and branch after landing"),
        )
        .arg(
            Arg::new("no-evidence")
                .long("no-evidence")
                .action(ArgAction::SetTrue)
                .help("Close without measured evidence; needs --reason and is audited"),
        )
        .arg(
            Arg::new("reason")
                .long("reason")
                .value_name("TEXT")
                .help("Why no evidence is recorded (with --no-evidence)"),
        )
        .arg(
            Arg::new("outcome")
                .long("outcome")
                .value_name("VALUE")
                .value_parser(gob_cli::clap::builder::PossibleValuesParser::new(
                    TicketOutcome::NAMES,
                ))
                .help("Outcome the ticket is closed with (default done)"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let reason = text(m, "reason");
        let no_evidence_reason = match (m.get_flag("no-evidence"), reason) {
            (true, Some(r)) if !r.trim().is_empty() => Some(r),
            (true, _) => {
                return Err(CliError::Usage(
                    "--no-evidence needs --reason <text> saying why no evidence is recorded"
                        .to_owned(),
                ));
            }
            (false, Some(_)) => {
                return Err(CliError::Usage(
                    "--reason is only used with --no-evidence".to_owned(),
                ));
            }
            (false, None) => None,
        };
        let outcome = match text(m, "outcome") {
            Some(s) => s
                .parse::<TicketOutcome>()
                .map_err(|e| CliError::Usage(format!("--outcome: {e}")))?,
            None => TicketOutcome::Done,
        };
        Ok(Self {
            opts: LandOptions {
                handle: text(m, "ticket"),
                dry_run: false,
                push: m.get_flag("push"),
                wait_secs: m.get_one::<u64>("wait").copied().unwrap_or(0),
                keep_worktree: m.get_flag("keep-worktree"),
                no_evidence_reason,
                outcome,
            },
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<LandOutcome> {
        let mut opts = self.opts.clone();
        opts.dry_run = ctx.dry_run;
        let out = land(&ctx.cwd, &opts)?;
        let already = out.already;
        let warnings = out.warnings.clone();
        let mut p = Payload::new(out).with_already(already);
        for w in warnings {
            p = p.with_warning(w);
        }
        Ok(p)
    }
}
