//! `ticket doctor`: ledger integrity.

use frob_ledger::TicketId;
use frob_ledger::doctor::Issue;
use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use super::{cli_err, open};

/// Output of `ticket doctor`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct DoctorData {
    /// Tickets examined.
    pub tickets: usize,
    /// Events examined.
    pub events: usize,
    /// True when no finding or issue remains.
    pub ok: bool,
    /// Problems that are not TICK rules.
    pub issues: Vec<Issue>,
    /// Tickets whose frontmatter `--fix` rewrote.
    pub fixed: Vec<TicketId>,
}

/// Re-fold every ticket and report frontmatter drift, dangling links and event-order problems.
#[derive(Debug, Clone, Copy, gob_cli::Command)]
#[command(
    verb = "ticket doctor",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct TicketDoctor {
    fix: bool,
}

impl Command for TicketDoctor {
    type Data = DoctorData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("fix")
                .long("fix")
                .action(ArgAction::SetTrue)
                .help("Rewrite frontmatter that differs from its events (TICK001)"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            fix: m.get_flag("fix"),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<DoctorData> {
        let ledger = open(ctx)?;
        let report = ledger.doctor(self.fix).map_err(cli_err)?;
        let ok = report.is_clean();
        let data = DoctorData {
            tickets: report.tickets,
            events: report.events,
            ok,
            issues: report.issues,
            fixed: report.fixed,
        };
        Ok(Payload::new(data).with_findings(report.findings))
    }
}
