//! `vet refresh [SOURCE] [--check]`: refresh the offline advisory snapshot from an advisory-db
//! checkout, or check how stale its `SNAPSHOT.toml` `as_of` stamp is.

// frob:ticket 01M6R956D5SKEVNBREQM8X95K5

use std::path::{Path, PathBuf};

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_path::Shown;
use gob_time::{Clock, Day};
use grimble_vet::{refresh, stamp_as_of};
use schemars::JsonSchema;
use serde::Serialize;

use crate::workspace::locate_root;

const DEFAULT_DB: &str = ".grimble/advisory-db";
/// Snapshot age in days beyond which `--check` reports it stale.
const DEFAULT_MAX_AGE: i64 = 30;

/// Refresh the advisory snapshot from an advisory-db checkout, or with --check report its staleness.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "vet refresh",
    product = "grimble",
    exits(ok, negative, usage, internal)
)]
pub struct VetRefresh {
    source: Option<String>,
    db: Option<String>,
    check: bool,
    max_age_days: Option<i64>,
}

/// `vet refresh` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct VetRefreshArgs {
    #[arg(help = "Path of an advisory-db checkout to copy RUSTSEC advisories from")]
    source: Option<String>,
    #[arg(
        long,
        help = "Snapshot directory to write or check (default .grimble/advisory-db)"
    )]
    db: Option<String>,
    #[arg(
        long,
        help = "Only check the snapshot's as_of age; exit 1 when stale, write nothing"
    )]
    check: bool,
    #[arg(
        long,
        help = "Days after which --check calls the snapshot stale (default 30)"
    )]
    max_age_days: Option<i64>,
}

/// Output of `vet refresh`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct VetRefreshData {
    /// The snapshot directory.
    pub db: String,
    /// The snapshot's `as_of` date after the run, when stamped.
    pub as_of: Option<String>,
    /// Advisories copied (0 for `--check`).
    pub copied: usize,
    /// Stale advisory files removed (0 for `--check`).
    pub removed: usize,
    /// Snapshot age in days at run time, when stamped.
    pub age_days: Option<i64>,
    /// Whether the snapshot is older than the allowed age (`--check` only).
    pub stale: bool,
}

/// Whole days between the stamp `as_of` and `today`; `None` when `as_of` is not a date.
fn age_days(as_of: &str, today: Day) -> Option<i64> {
    as_of.parse::<Day>().ok().map(|d| today.days_since(d))
}

/// Resolve the snapshot directory against `root`.
fn db_dir(root: &Path, db: Option<&str>) -> PathBuf {
    root.join(db.unwrap_or(DEFAULT_DB))
}

/// Report the staleness of the snapshot at `dir` as of `today`; `Err` when it is stale or unstamped.
///
/// # Errors
/// [`CliError::Gate`] when the snapshot has no stamp or is older than `max_age` days.
pub fn check_staleness(dir: &Path, today: Day, max_age: i64) -> Result<VetRefreshData, CliError> {
    let as_of = stamp_as_of(dir);
    let age = as_of.as_deref().and_then(|a| age_days(a, today));
    let stale = age.is_none_or(|a| a > max_age);
    let data = VetRefreshData {
        db: Shown::of(dir).to_string(),
        as_of,
        copied: 0,
        removed: 0,
        age_days: age,
        stale,
    };
    if stale {
        let message = match age {
            Some(a) => format!("advisory snapshot is {a} days old (limit {max_age})"),
            None => format!(
                "advisory snapshot at {} has no SNAPSHOT.toml as_of",
                data.db
            ),
        };
        tracing::warn!(%message, "advisory snapshot stale");
        let value = serde_json::to_value(&data).map_err(CliError::internal)?;
        return Err(CliError::Gate {
            message,
            data: value,
            warnings: Vec::new(),
        });
    }
    tracing::info!(age_days = ?age, "advisory snapshot is fresh");
    Ok(data)
}

/// Copy the checkout at `source` into the snapshot `dir`, stamped `today`.
///
/// # Errors
/// [`CliError::Usage`] when `source` is not a directory or an advisory is invalid.
pub fn run_refresh(source: &Path, dir: &Path, today: Day) -> Result<VetRefreshData, CliError> {
    if !source.is_dir() {
        return Err(CliError::Usage(format!(
            "no advisory-db checkout at {}",
            Shown::of(source)
        )));
    }
    let report =
        refresh(source, dir, &today.to_string()).map_err(|e| CliError::Usage(e.to_string()))?;
    Ok(VetRefreshData {
        db: Shown::of(dir).to_string(),
        as_of: Some(today.to_string()),
        copied: report.copied,
        removed: report.removed,
        age_days: Some(0),
        stale: false,
    })
}

impl Command for VetRefresh {
    type Data = VetRefreshData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<VetRefreshArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<VetRefreshArgs>(m)?;
        Ok(Self {
            source: a.source,
            db: a.db,
            check: a.check,
            max_age_days: a.max_age_days,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<VetRefreshData> {
        let root = locate_root(&ctx.cwd);
        let dir = db_dir(&root, self.db.as_deref());
        let today = Day::of(ctx.clock.now());
        let data = match (&self.source, self.check) {
            (None, _) | (_, true) => {
                check_staleness(&dir, today, self.max_age_days.unwrap_or(DEFAULT_MAX_AGE))?
            }
            (Some(src), false) => {
                if ctx.dry_run {
                    return Err(CliError::Usage(
                        "vet refresh writes files; no --dry-run".into(),
                    ));
                }
                run_refresh(&root.join(src), &dir, today)?
            }
        };
        let row = format!(
            "snapshot {} as_of {} (copied {}, removed {})",
            data.db,
            data.as_of.as_deref().unwrap_or("unstamped"),
            data.copied,
            data.removed
        );
        Ok(Payload::new(data).with_rendered(vec![row]))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn day(s: &str) -> Day {
        s.parse().expect("test date")
    }

    // frob:tests crates/grimble/src/vet_refresh.rs::check_staleness
    #[test]
    fn a_fresh_stamp_passes_and_an_old_or_missing_one_fails() {
        let dir = tempfile::tempdir().expect("tmp");
        assert!(check_staleness(dir.path(), day("2026-11-06"), 30).is_err());
        std::fs::write(
            dir.path().join("SNAPSHOT.toml"),
            "as_of = \"2026-11-01\"\ncount = 0\n",
        )
        .expect("write");
        let ok = check_staleness(dir.path(), day("2026-11-06"), 30).expect("fresh");
        assert_eq!(ok.age_days, Some(5));
        assert!(check_staleness(dir.path(), day("2027-01-01"), 30).is_err());
    }

    // frob:tests crates/grimble/src/vet_refresh.rs::run_refresh
    #[test]
    fn refresh_copies_advisories_and_stamps_today() {
        let src = tempfile::tempdir().expect("src");
        let dst = tempfile::tempdir().expect("dst");
        let out = run_refresh(src.path(), &dst.path().join("db"), day("2026-11-06")).expect("ok");
        assert_eq!(out.copied, 0);
        assert_eq!(
            stamp_as_of(&dst.path().join("db")).as_deref(),
            Some("2026-11-06")
        );
        assert!(run_refresh(&src.path().join("nope"), dst.path(), day("2026-11-06")).is_err());
    }
}
