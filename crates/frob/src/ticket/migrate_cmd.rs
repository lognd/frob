//! `ticket migrate --to-branch`: copy the legacy `tickets/` ledger onto the orphan ticket branch (`navigation.md` 2.3).

use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use super::{cli_err, open};

/// One ticket and the path it gets on the ticket branch.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct MappedTicket {
    /// The ticket ULID.
    pub id: String,
    /// Branch-relative path of its file.
    pub path: String,
}

/// Output of `ticket migrate --to-branch`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct MigrateData {
    /// The orphan branch the ledger was copied to.
    pub branch: String,
    /// Tickets moved.
    pub tickets: usize,
    /// Ticket event files copied byte for byte.
    pub events: usize,
    /// Milestone and cycle files copied.
    pub object_files: usize,
    /// Tickets whose old `ticket.md` differed from the fold of its events (the fold is what moves).
    pub drifted: Vec<String>,
    /// The migration commit; absent for a dry run or when the branch already held the ledger.
    pub commit: Option<String>,
    /// True for a dry run: nothing was written.
    pub dry_run: bool,
    /// Every ticket's target path (dry run only; the branch itself lists them otherwise).
    pub mapping: Vec<MappedTicket>,
}

/// Copy the legacy ledger onto the orphan ticket branch and verify it; `--dry-run` prints the mapping and writes nothing.
#[derive(Debug, Clone, Copy, gob_cli::Command)]
#[command(
    verb = "ticket migrate",
    product = "frob",
    idempotent = true,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct Migrate;

impl Command for Migrate {
    type Data = MigrateData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("to-branch")
                .long("to-branch")
                .action(ArgAction::SetTrue)
                .required(true)
                .help("Move the ledger onto the orphan ticket branch (the only migration so far)"),
        )
    }

    fn from_matches(_m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> CliOutcome<MigrateData> {
        let ledger = open(ctx)?;
        let report = ledger.migrate_to_branch(ctx.dry_run).map_err(|e| match e {
            frob_ledger::LedgerError::Invalid { message } => {
                Refusal::new("E-TICKET-MIGRATE", RefusalClass::GuardNeedsAction, message).into()
            }
            other => cli_err(other),
        })?;
        tracing::info!(branch = %report.branch, tickets = report.tickets, already = report.already, dry_run = ctx.dry_run, "ticket migrate finished");
        let mapping = if ctx.dry_run {
            report
                .mapping
                .iter()
                .map(|(id, path)| MappedTicket {
                    id: id.to_string(),
                    path: path.clone(),
                })
                .collect()
        } else {
            Vec::new()
        };
        Ok(Payload::new(MigrateData {
            branch: report.branch,
            tickets: report.tickets,
            events: report.events,
            object_files: report.object_files,
            drifted: report.drifted.iter().map(ToString::to_string).collect(),
            commit: report.commit.map(|c| c.to_string()),
            dry_run: ctx.dry_run,
            mapping,
        })
        .with_already(report.already))
    }
}
