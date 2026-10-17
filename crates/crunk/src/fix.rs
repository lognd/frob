//! `fix [--dry-run]`: apply the Tier A (machine-applicable) fixes of `crunk check`.
//!
//! Only stylesheet sites are fixed; a dry run prints the same diff the real run applies and
//! writes nothing. The engine is [`crunk_fix`].

// frob:ticket 01M43ATCQVX9A1TJ6A4AE48FDX

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;

/// Apply (or with `--dry-run` only show) the machine-applicable fixes.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "fix",
    product = "crunk",
    idempotent = false,
    exits(ok, refused, usage, internal)
)]
pub struct Fix {
    dry_run: bool,
}

/// `Fix` arguments.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct FixArgs {
    #[arg(long, help = "Show the diff and write nothing")]
    dry_run: bool,
}

/// The diff of one file.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct FileChange {
    /// File path relative to the repository root.
    pub path: String,
    /// ASCII hunks, one per edit.
    pub diff: String,
}

/// Output of `fix`.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, JsonSchema)]
pub struct FixData {
    /// Whether nothing was written.
    pub dry_run: bool,
    /// Fixes accepted by the planner.
    pub accepted: usize,
    /// Fixes the planner refused (overlap, tier, invalid).
    pub dropped: usize,
    /// Fixes refused because the site is not a stylesheet.
    pub skipped_non_stylesheet: usize,
    /// Rules of fixes skipped as stale or out of range.
    pub skipped: Vec<String>,
    /// Per-file diffs.
    pub files: Vec<FileChange>,
}

impl Command for Fix {
    type Data = FixData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<FixArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<FixArgs>(m)?;
        Ok(Self { dry_run: a.dry_run })
    }

    fn run(&self, ctx: &Context) -> Outcome<FixData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let report = crunk_fix::run(&root, self.dry_run).map_err(|e| {
            tracing::warn!(error = %e, "fix pass failed");
            Refusal::new("E-FIX", RefusalClass::GuardNeedsAction, e.to_string())
                .with_remedy("resolve the error above, then rerun")
        })?;
        let data = FixData {
            dry_run: report.dry_run,
            accepted: report.plan.accepted.len(),
            dropped: report.plan.dropped.len(),
            skipped_non_stylesheet: report.skipped_non_stylesheet,
            skipped: report.applied.skipped.clone(),
            files: report
                .applied
                .diffs
                .iter()
                .map(|d| FileChange {
                    path: d.path.clone(),
                    diff: d.diff.clone(),
                })
                .collect(),
        };
        let mut lines: Vec<String> = data
            .files
            .iter()
            .flat_map(|f| f.diff.lines().map(str::to_owned))
            .collect();
        if lines.is_empty() {
            lines.push("no fixes to apply".to_owned());
        }
        Ok(Payload::new(data).with_rendered(lines))
    }
}
