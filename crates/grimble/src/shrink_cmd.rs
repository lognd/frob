//! `shrink [--apply]`: propose removing `may` grants no detector observes (CAP002) and `owns` selectors for unowned directories (SYS001).
//!
//! Binds the repo with `grimble_check::bind_repo`, plans with `grimble_bind::shrink::plan` and
//! prints the removal diff. The model files are written only under `--apply`. With `--apply` on a
//! terminal, each grant is first offered an excuse prompt: a reason keeps it and writes an
//! `// kept` comment after it; a blank answer removes it. Non-terminal runs never prompt.

// frob:ticket 01M5A5F8CN6EKHGV1C4QZCQZMP
// frob:ticket 01M5A7E4S1CQJ834X4409EPWW0

use std::io::{IsTerminal, stderr, stdin};

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use grimble_bind::shrink::{self, OwnsAddition, Removal};
use schemars::JsonSchema;
use serde::Serialize;

use crate::workspace::{check_error, locate_root};

/// Propose (and with `--apply` perform) removal of unobserved grants and owns for unowned dirs.
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

/// One proposed `owns` addition, as reported.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct OwnsRow {
    /// Repo-relative `.grmb` file the clause is written into.
    pub file: String,
    /// The node that gains the selector.
    pub node: String,
    /// The `owns` clause to write.
    pub clause: String,
    /// The unowned directory the selector covers.
    pub dir: String,
    /// 1-based line the clause is inserted at.
    pub line: usize,
}

impl From<&OwnsAddition> for OwnsRow {
    fn from(a: &OwnsAddition) -> Self {
        Self {
            file: a.file.clone(),
            node: a.node.clone(),
            clause: a.clause.clone(),
            dir: a.dir.clone(),
            line: a.line,
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
    /// Every proposed `owns` selector for a directory SYS001 reports unowned.
    pub owns_additions: Vec<OwnsRow>,
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
        let interactive = self.apply && stdin().is_terminal() && stderr().is_terminal();
        tracing::info!(interactive, "shrink excuse prompt mode");
        let mut decide = |r: &Removal| {
            if interactive {
                // frob:defer LOG001 because="the excuse prompt is user-facing TTY output, not a log line" ticket=01M79PWQP03T5YH7QVM72KW077
                shrink::prompt_excuse(r, &mut stdin().lock(), &mut stderr())
            } else {
                None
            }
        };
        let plan = shrink::plan_with_decider(
            &binding.findings,
            &binding.owns_sites,
            &mut read,
            &mut decide,
        );
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
            owns_additions: plan.additions.iter().map(OwnsRow::from).collect(),
            diff: plan.diff,
            skipped: plan.skipped,
        };
        let already = data.removals.is_empty() && data.owns_additions.is_empty();
        Ok(Payload::new(data)
            .with_rendered(rendered)
            .with_already(already))
    }
}
