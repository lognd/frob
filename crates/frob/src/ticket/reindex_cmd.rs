//! `ticket reindex`: move ticket files to their computed paths in a reindex commit (`navigation.md` 2.2).
// frob:ticket 01M3ZX85X37W6QSQSJD1WYVKZG

use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use super::{cli_err, open};

/// Most diff lines `--check` prints before summarising the rest.
const DIFF_CAP: usize = 50;

/// One ticket file the reindex moves.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct MovedFile {
    /// Old branch-relative path.
    pub from: String,
    /// New branch-relative path.
    pub to: String,
}

/// Output of `ticket reindex`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ReindexData {
    /// Ticket files moved (or, with `--check`, that would move).
    pub moved: Vec<MovedFile>,
    /// Files the reindex commit writes or deletes, moves included.
    pub files: usize,
    /// The reindex commit, when one was written.
    pub commit: Option<String>,
    /// With `--check` on a stale branch, the capped diff (one line per file); empty otherwise.
    pub diff: String,
}

/// Move ticket files to the paths their titles and parents imply, in one `tickets(reindex)` commit; `--check` changes nothing and exits 1 with the diff when the branch is stale.
#[derive(Debug, Clone, Copy, gob_cli::Command)]
#[command(
    verb = "ticket reindex",
    product = "frob",
    idempotent = true,
    exits(ok, negative, refused, usage, internal)
)]
pub struct Reindex {
    check: bool,
}

impl Command for Reindex {
    type Data = ReindexData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("check")
                .long("check")
                .action(ArgAction::SetTrue)
                .help("Write nothing; print the diff and exit 1 when the ticket branch is not current"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            check: m.get_flag("check"),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ReindexData> {
        let ledger = open(ctx)?;
        let plan = ledger.reindex_plan().map_err(cli_err)?;
        let moved: Vec<MovedFile> = plan
            .moves
            .iter()
            .map(|m| MovedFile {
                from: m.from.clone(),
                to: m.to.clone(),
            })
            .collect();
        let current = plan.changes.is_empty();
        if self.check && !current {
            let data = ReindexData {
                moved,
                files: plan.changes.len(),
                commit: None,
                diff: plan.diff(DIFF_CAP),
            };
            return Err(CliError::Gate {
                message: format!("ticket branch is not reindexed:\n{}", data.diff),
                data: serde_json::to_value(&data).map_err(CliError::internal)?,
                warnings: Vec::new(),
            });
        }
        let commit = if self.check || current {
            None
        } else {
            ledger.reindex_commit(None).map_err(cli_err)?
        };
        tracing::info!(
            check = self.check,
            files = plan.changes.len(),
            "ticket reindex"
        );
        Ok(Payload::new(ReindexData {
            moved,
            files: plan.changes.len(),
            commit: commit.map(|c| c.to_string()),
            diff: String::new(),
        })
        .with_already(current))
    }
}
