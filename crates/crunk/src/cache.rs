//! `cache ls` and `cache prune`: inspect and trim the per-user check cache of this repository.
//!
//! The cache is the shared `gob-cache` database under `$XDG_CACHE_HOME/frob/cache/<repo-id>/crunk`.
//! `ls` reports its location, size and row counts; `prune` deletes the rows no run of this build
//! can hit (other engines), or every row under `--all`. Both are safe at any time: the cache is
//! regenerable (a miss only costs a re-ingest).

// frob:ticket 01M4MD9FEH1F337CTWPZ03B67Y

use std::path::Path;

use gob_cache::{Cache, DB_FILE};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;

/// The state-dir name the check keeps its cache under (`.crunk`).
fn state_dir() -> String {
    format!(".{PRODUCT}")
}

/// Output of `cache ls`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CacheLsData {
    /// The cache directory, absent when no per-user cache location is derivable.
    pub dir: Option<String>,
    /// True when the database file exists.
    pub present: bool,
    /// Size of the database file in bytes.
    pub bytes: u64,
    /// Parse artifact rows.
    pub artifacts: u64,
    /// Per-file findings rows.
    pub findings: u64,
    /// Repo-scope findings rows.
    pub repo_rule: u64,
}

/// Output of `cache prune`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CachePruneData {
    /// True when nothing was deleted because of `--dry-run` or an absent cache.
    pub dry_run: bool,
    /// Artifact rows deleted.
    pub artifacts: u64,
    /// Per-file findings rows deleted.
    pub findings: u64,
    /// Repo-scope findings rows deleted.
    pub repo_rule: u64,
}

/// The cache directory of `root`, when one is derivable.
fn cache_dir(root: &Path) -> Option<std::path::PathBuf> {
    gob_cache::shared_dir(root, &state_dir())
}

/// List the location, size and row counts of the repository's check cache.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "cache ls",
    product = "crunk",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct CacheLs;

impl Command for CacheLs {
    type Data = CacheLsData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd
    }

    fn from_matches(_m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<CacheLsData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let data = ls(&root);
        tracing::info!(present = data.present, bytes = data.bytes, "cache ls");
        let line = match &data.dir {
            Some(dir) => format!(
                "{dir}: {} bytes, {} artifacts, {} findings, {} repo rows",
                data.bytes, data.artifacts, data.findings, data.repo_rule
            ),
            None => "no per-user cache location".to_owned(),
        };
        Ok(Payload::new(data).with_rendered(vec![line]))
    }
}

/// The `cache ls` report for `root`; reading never creates the cache.
fn ls(root: &Path) -> CacheLsData {
    let Some(dir) = cache_dir(root) else {
        return CacheLsData {
            dir: None,
            present: false,
            bytes: 0,
            artifacts: 0,
            findings: 0,
            repo_rule: 0,
        };
    };
    let db = dir.join(DB_FILE);
    let present = db.is_file();
    let stats = if present {
        Cache::open(&dir).stats()
    } else {
        gob_cache::CacheStats::default()
    };
    CacheLsData {
        dir: Some(dir.display().to_string()),
        present,
        bytes: std::fs::metadata(&db).map_or(0, |m| m.len()),
        artifacts: stats.artifacts,
        findings: stats.findings,
        repo_rule: stats.repo_rule,
    }
}

/// `cache prune` flags.
#[derive(Debug, Clone, gob_cli::clap::Args)]
#[command(about = None, long_about = None)]
struct PruneArgs {
    #[arg(long, help = "Delete every row, not only those of other engines")]
    all: bool,
}

/// Delete cache rows no run of this build can hit, or every row with `--all`.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "cache prune",
    product = "crunk",
    idempotent = true,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct CachePrune {
    all: bool,
}

impl Command for CachePrune {
    type Data = CachePruneData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<PruneArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            all: gob_cli::parse::<PruneArgs>(m)?.all,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<CachePruneData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let present = cache_dir(&root).is_some_and(|d| d.join(DB_FILE).is_file());
        let pruned = if present && !ctx.dry_run {
            let dir = cache_dir(&root).unwrap_or_default();
            Cache::open(&dir)
                .with_engine(gob_check::engine_fingerprint())
                .prune(self.all)
        } else {
            gob_cache::Pruned::default()
        };
        tracing::info!(all = self.all, total = pruned.total(), "cache prune");
        let data = CachePruneData {
            dry_run: ctx.dry_run || !present,
            artifacts: pruned.artifacts,
            findings: pruned.findings,
            repo_rule: pruned.repo_rule,
        };
        let line = format!("pruned {} rows", pruned.total());
        Ok(Payload::new(data).with_rendered(vec![line]))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk/src/cache.rs::ls
    #[test]
    fn ls_of_an_unborn_cache_is_absent_and_creates_nothing() {
        let dir = tempfile::tempdir().expect("tempdir");
        let data = ls(dir.path());
        assert!(!data.present);
        assert_eq!(data.bytes, 0);
        if let Some(d) = data.dir {
            assert!(!Path::new(&d).join(DB_FILE).exists());
        }
    }
}
