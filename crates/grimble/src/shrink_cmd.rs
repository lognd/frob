//! `shrink [--apply]`: propose removing `may` grants that no detector observes (CAP002).
//!
//! Binds the repo with `grimble_check::bind_repo`, plans with `grimble_bind::shrink::plan` and
//! prints the removal diff. The model files are written only under `--apply`.

// frob:ticket 01M5A5F8CN6EKHGV1C4QZCQZMP

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use grimble_bind::shrink::{self, Removal};
use schemars::JsonSchema;
use serde::Serialize;

use crate::workspace::{check_error, locate_root};

/// Propose (and with `--apply` perform) removal of grants no detector observes.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "shrink",
    product = "grimble",
    idempotent = true,
    exits(ok, usage, internal)
)]
pub struct Shrink {
    apply: bool,
}

/// `Shrink` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ShrinkArgs {
    #[arg(
        long,
        help = "Write the removals to the model files (default: print the diff only)"
    )]
    apply: bool,
}

/// One proposed removal, as reported.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct RemovalRow {
    /// Repo-relative `.grmb` file.
    pub file: String,
    /// The node the grant belongs to.
    pub node: String,
    /// The grant clause as written.
    pub clause: String,
    /// 1-based line of the clause.
    pub line: usize,
    /// The clause to write instead to keep the grant with a reason.
    pub excuse_hint: String,
}

impl From<&Removal> for RemovalRow {
    fn from(r: &Removal) -> Self {
        Self {
            file: r.file.clone(),
            node: r.node.clone(),
            clause: r.clause.clone(),
            line: r.line,
            excuse_hint: r.excuse_hint.clone(),
        }
    }
}

/// Output of `shrink`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ShrinkData {
    /// True when the removals were written to disk.
    pub applied: bool,
    /// Every proposed removal.
    pub removals: Vec<RemovalRow>,
    /// The unified-style diff of all edits; empty when nothing is proposed.
    pub diff: String,
    /// Findings shrink could not act on.
    pub skipped: Vec<String>,
}

impl Command for Shrink {
    type Data = ShrinkData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<ShrinkArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ShrinkArgs>(m)?;
        Ok(Self { apply: a.apply })
    }

    fn run(&self, ctx: &Context) -> Outcome<ShrinkData> {
        let root = locate_root(&ctx.cwd);
        let binding = grimble_check::bind_repo(&root).map_err(check_error)?;
        let mut read = |f: &str| std::fs::read_to_string(root.join(f)).ok();
        let plan = shrink::plan(&binding.findings, &mut read);
        let applied = self.apply && !plan.edited.is_empty();
        if applied {
            plan.apply(&root).map_err(CliError::internal)?;
            tracing::info!(files = plan.edited.len(), "shrink applied");
        } else {
            tracing::info!(apply = self.apply, "shrink wrote nothing");
        }
        let rendered = plan.diff.lines().map(str::to_owned).collect();
        let data = ShrinkData {
            applied,
            removals: plan.removals.iter().map(RemovalRow::from).collect(),
            diff: plan.diff,
            skipped: plan.skipped,
        };
        let already = data.removals.is_empty();
        Ok(Payload::new(data)
            .with_rendered(rendered)
            .with_already(already))
    }
}
