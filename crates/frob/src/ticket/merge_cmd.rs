//! `merge-driver`: the hidden verb git invokes for conflicted `ticket.md`, `milestone.md` and `cycle.md` files.

use std::path::PathBuf;

use frob_ledger::event::Event;
use frob_ledger::merge::{locate, resolve_at};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use super::open;

/// Refs that name a side of an in-progress merge, cherry-pick or rebase.
const SIDE_REFS: [&str; 4] = ["HEAD", "MERGE_HEAD", "CHERRY_PICK_HEAD", "REBASE_HEAD"];
/// Prefix of the environment variables `git merge` sets, one per merged commit.
const GITHEAD_PREFIX: &str = "GITHEAD_";

/// Commits to read events from: our checkout, in-progress refs, and every `GITHEAD_<oid>`.
///
/// `git merge` exports `GITHEAD_<oid>=<name>` for each commit it merges before
/// it runs any merge driver, while `MERGE_HEAD` is written only afterwards.
fn side_commits(ledger: &frob_ledger::Ledger) -> Vec<String> {
    let mut sides: Vec<String> = SIDE_REFS
        .iter()
        .filter_map(|name| ledger.repo().rev_parse(name).ok())
        .map(|oid| oid.to_string())
        .collect();
    for (key, _) in std::env::vars() {
        if let Some(oid) = key.strip_prefix(GITHEAD_PREFIX)
            && oid.len() == 40
            && oid.bytes().all(|b| b.is_ascii_hexdigit())
        {
            sides.push(oid.to_ascii_lowercase());
        }
    }
    sides.sort();
    sides.dedup();
    sides
}

/// Output of `merge-driver`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct MergeData {
    /// The ticket, milestone or cycle whose frontmatter was re-folded.
    pub ticket: String,
    /// Events in the union.
    pub events: usize,
    /// Events found in git history of the other sides but not yet on disk.
    pub from_history: usize,
}

/// Union both sides' event files of a conflicted ticket.md and re-fold it (git invokes this).
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "merge-driver",
    product = "frob",
    idempotent = true,
    exits(ok, negative, usage, internal)
)]
pub struct MergeDriver {
    base: PathBuf,
    ours: PathBuf,
    theirs: PathBuf,
    path: String,
}

impl MergeDriver {
    /// Resolve a conflicted `milestone.md` or `cycle.md` through `frob_pm::merge::resolve`.
    fn run_pm(&self, ctx: &Context) -> CliOutcome<MergeData> {
        let ledger = open(ctx)?;
        let (kind, id) = frob_pm::merge::object_of_path(&self.path)
            .map_err(|e| CliError::Usage(e.to_string()))?;
        let root = ledger
            .repo()
            .work_dir()
            .map_or_else(|| ctx.cwd.clone(), std::path::Path::to_path_buf);
        let store = frob_pm::PmStore::new(&ledger);
        let mut extra = Vec::new();
        for side in side_commits(&ledger) {
            match store.read_events_at(&side, kind, id) {
                Ok(mut events) => extra.append(&mut events),
                Err(e) => tracing::debug!(side, error = %e, "no events readable from this side"),
            }
        }
        let ours = if self.ours.is_absolute() {
            self.ours.clone()
        } else {
            ctx.cwd.join(&self.ours)
        };
        let report = frob_pm::merge::resolve_with(&root, &self.path, &ours, extra)
            .map_err(|e| CliError::Negative(e.to_string()))?;
        tracing::info!(path = %self.path, events = report.events, "pm object merged");
        Ok(Payload::new(MergeData {
            ticket: report.id.to_string(),
            events: report.events,
            from_history: report.from_extra,
        }))
    }
}

/// The positionals of the git merge driver, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct MergeArgs {
    #[arg(help = "Common ancestor version (%O); read only to find the ticket id")]
    base: String,
    #[arg(help = "Our version (%A); the result is written here")]
    ours: String,
    #[arg(help = "Their version (%B); read only to find the ticket id")]
    theirs: String,
    #[arg(help = "Repo-relative path of the file (%P)")]
    path: String,
}

impl Command for MergeDriver {
    type Data = MergeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<MergeArgs>(cmd.hide(true))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<MergeArgs>(m)?;
        Ok(Self {
            base: PathBuf::from(a.base),
            theirs: PathBuf::from(a.theirs),
            ours: PathBuf::from(a.ours),
            path: a.path,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<MergeData> {
        if frob_pm::merge::object_of_path(&self.path).is_ok() {
            return self.run_pm(ctx);
        }
        let abs = |p: &PathBuf| {
            if p.is_absolute() {
                p.clone()
            } else {
                ctx.cwd.join(p)
            }
        };
        let ours = abs(&self.ours);
        let texts: Vec<String> = [&ours, &abs(&self.base), &abs(&self.theirs)]
            .into_iter()
            .map(|p| std::fs::read_to_string(p).unwrap_or_default())
            .collect();
        let versions: Vec<&str> = texts.iter().map(String::as_str).collect();
        let (layout, id) =
            locate(&self.path, &versions).map_err(|e| CliError::Usage(e.to_string()))?;
        let ledger = open(ctx)?.with_layout(layout);
        let root = ledger
            .repo()
            .work_dir()
            .map_or_else(|| ctx.cwd.clone(), std::path::Path::to_path_buf);
        // Git may run the driver before it has checked out the other side's
        // event files, so also read them from the commits being merged.
        let mut extra: Vec<Event> = Vec::new();
        for side in side_commits(&ledger) {
            match ledger.read_events_at(&side, id) {
                Ok(mut events) => extra.append(&mut events),
                Err(e) => tracing::debug!(side, error = %e, "no events readable from this side"),
            }
        }
        tracing::debug!(path = %self.path, ?layout, %id, "merge driver located the ticket");
        let report = resolve_at(&root, &self.path, layout, id, &ours, extra)
            .map_err(|e| CliError::Negative(e.to_string()))?;
        Ok(Payload::new(MergeData {
            ticket: report.ticket.to_string(),
            events: report.events,
            from_history: report.from_extra,
        }))
    }
}
