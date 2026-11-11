//! `frob coord status`: list the live full `frob check` runs of every worktree.
//!
//! Each worktree's `.frob/check.lock` (pid, start time, argv) is read through
//! [`frob_check::live_holder`]; worktrees with no lock or a dead holder are omitted.

// frob:ticket 01M5B6QR4JZ19YAGB7922H0R69

use std::path::Path;

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use gob_path::Shown;

use crate::pretty::PrettyExt;
use crate::workspace::Located;

/// One live full check in one worktree.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct LiveCheck {
    /// Worktree root holding the lock.
    pub worktree: String,
    /// Branch checked out there, when any.
    pub branch: Option<String>,
    /// Process id of the holder.
    pub pid: u32,
    /// Unix seconds when the holder took the lock.
    pub started: u64,
    /// The holder's command line.
    pub argv: Vec<String>,
    /// True when the holder is the post-commit hook's background check.
    pub speculative: bool,
}

/// Output of `frob coord status`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CoordStatusData {
    /// Live full checks, one per worktree that has a live holder.
    pub checks: Vec<LiveCheck>,
}

/// The live check of the worktree at `path`, if its lock has a live holder.
fn live_check(path: &Path, branch: Option<String>) -> Option<LiveCheck> {
    let h = frob_check::live_holder(path)?;
    Some(LiveCheck {
        worktree: Shown::of(path).to_string(),
        branch,
        pid: h.pid,
        started: h.started,
        argv: h.argv,
        speculative: h.speculative,
    })
}

/// List the live full `frob check` runs of every worktree of this repository.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "coord status",
    product = "frob",
    exits(ok, refused, usage, internal)
)]
pub struct CoordStatus;

impl Command for CoordStatus {
    type Data = CoordStatusData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd
    }

    fn from_matches(_m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<CoordStatusData> {
        let (repo, _) = Located::discover(&ctx.cwd).into_repo()?;
        let trees = repo.list_worktrees().map_err(CliError::internal)?;
        let checks: Vec<LiveCheck> = trees
            .into_iter()
            .filter_map(|w| live_check(&w.path, w.branch))
            .collect();
        tracing::info!(live = checks.len(), "coord status read");
        let rows = if checks.is_empty() {
            vec!["no live full checks".to_string()]
        } else {
            checks
                .iter()
                .map(|c| {
                    format!(
                        "{} pid {} since {}{}: {}",
                        c.worktree,
                        c.pid,
                        c.started,
                        if c.speculative { " (speculative)" } else { "" },
                        c.argv.join(" ")
                    )
                })
                .collect()
        };
        Ok(Payload::new(CoordStatusData { checks }).with_pretty(rows))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob/src/coord_cmd.rs::live_check
    #[test]
    fn live_check_reports_live_holder_only() {
        let dir = tempfile::tempdir().unwrap();
        assert!(live_check(dir.path(), None).is_none());
        std::fs::create_dir(dir.path().join(".frob")).unwrap();
        let body = |pid: u32| {
            format!(r#"{{"pid":{pid},"started":7,"argv":["frob","check"],"speculative":false}}"#)
        };
        // pid u32::MAX - 1 is never a live process.
        std::fs::write(dir.path().join(".frob/check.lock"), body(u32::MAX - 1)).unwrap();
        assert!(live_check(dir.path(), None).is_none());
        std::fs::write(
            dir.path().join(".frob/check.lock"),
            body(std::process::id()),
        )
        .unwrap();
        let c = live_check(dir.path(), Some("b".into())).unwrap();
        assert_eq!((c.pid, c.started), (std::process::id(), 7));
        assert_eq!(c.argv, ["frob", "check"]);
    }
}
