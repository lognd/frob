//! `frob migrate`: convert the old `frob-ratchet.lock.json` into `frob-baseline.toml`, once.
//!
//! The conversion keeps every locked key under one reason and owning ticket, writes the baseline,
//! and deletes the lock. A second run finds the baseline in place and changes nothing.

// frob:ticket 01M66G70F82EC8EERE0077QKVV

use std::path::Path;

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_rules::{BASELINE_FILE, Baseline, BaselineError, RATCHET_LOCK_FILE, migrate_ratchet_lock};
use schemars::JsonSchema;
use serde::Serialize;

use crate::pretty::PrettyExt;
use crate::ticket::{open, resolve};
use crate::workspace::Located;

/// Output of `frob migrate`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct MigrateData {
    /// Whether the lock was converted on this run (false when nothing was to do).
    pub migrated: bool,
    /// Baseline keys written.
    pub keys: usize,
    /// The baseline file, relative to the repository root.
    pub path: String,
}

/// The flags of `migrate`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct MigrateArgs {
    #[arg(long, required = true, help = "Why the locked debt is accepted")]
    reason: String,
    #[arg(long, required = true, help = "Ticket that owns paying it down")]
    ticket: String,
}

/// Convert `frob-ratchet.lock.json` into `frob-baseline.toml` once, then delete the lock.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "migrate",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Migrate {
    reason: String,
    ticket: String,
}

/// What a migration did at a repository root.
#[derive(Debug, PartialEq, Eq)]
pub enum Migrated {
    /// No lock file exists; nothing to convert.
    NoLock,
    /// A baseline already exists; the lock (if any) was left alone.
    AlreadyDone,
    /// The lock was converted into this many baseline keys and removed.
    Converted(usize),
}

/// Convert the lock at `root` into the baseline file, deleting the lock after a successful write.
///
/// # Errors
/// [`CliError`] on a bad lock, bad baseline, or filesystem failure.
pub fn migrate_at(root: &Path, reason: &str, ticket: &str) -> Result<Migrated, CliError> {
    let lock_path = root.join(RATCHET_LOCK_FILE);
    let base_path = root.join(BASELINE_FILE);
    let lock = match std::fs::read_to_string(&lock_path) {
        Ok(t) => t,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            tracing::info!("migrate: no {RATCHET_LOCK_FILE}");
            return Ok(Migrated::NoLock);
        }
        Err(e) => return Err(CliError::internal(e)),
    };
    let existing = match std::fs::read_to_string(&base_path) {
        Ok(t) => Some(Baseline::parse(&t).map_err(|e| CliError::Usage(e.to_string()))?),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => None,
        Err(e) => return Err(CliError::internal(e)),
    };
    match migrate_ratchet_lock(&lock, existing.as_ref(), reason, ticket) {
        Err(BaselineError::AlreadyMigrated) => {
            tracing::info!("migrate: baseline already present, lock left in place");
            Ok(Migrated::AlreadyDone)
        }
        Err(e) => Err(CliError::Usage(e.to_string())),
        Ok(baseline) => {
            gob_fs::write_atomic(&base_path, baseline.render().as_bytes())
                .map_err(CliError::internal)?;
            std::fs::remove_file(&lock_path).map_err(CliError::internal)?;
            let keys = baseline.key_count();
            tracing::info!(keys, "migrate: converted the ratchet lock");
            Ok(Migrated::Converted(keys))
        }
    }
}

impl Command for Migrate {
    type Data = MigrateData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<MigrateArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<MigrateArgs>(m)?;
        Ok(Self {
            reason: a.reason,
            ticket: a.ticket,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<MigrateData> {
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let handle = ledger
            .show(id)
            .map_err(crate::ticket::cli_err)?
            .summary
            .handle;
        let done = migrate_at(&root, &self.reason, &handle)?;
        let (migrated, keys, row) = match done {
            Migrated::NoLock => (
                false,
                0,
                format!("no {RATCHET_LOCK_FILE}; nothing to migrate"),
            ),
            Migrated::AlreadyDone => (
                false,
                0,
                format!("{BASELINE_FILE} already exists; nothing migrated"),
            ),
            Migrated::Converted(n) => (
                true,
                n,
                format!("migrated {n} key(s) from {RATCHET_LOCK_FILE} into {BASELINE_FILE}"),
            ),
        };
        Ok(Payload::new(MigrateData {
            migrated,
            keys,
            path: BASELINE_FILE.to_owned(),
        })
        .with_pretty(vec![row]))
    }
}

/// Register the `migrate` verb.
pub fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<Migrate>()
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A lock with three 64-digit hex fingerprints across two rules.
    fn lock() -> String {
        format!(
            r#"{{"DOC001": ["{}", "{}"], "ZED001": ["{}"]}}"#,
            "a".repeat(64),
            "b".repeat(64),
            "c".repeat(64)
        )
    }

    // frob:tests crates/frob/src/migrate_cmd.rs::migrate_at
    #[test]
    fn migrate_converts_the_lock_once_and_removes_it() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join(RATCHET_LOCK_FILE), lock()).unwrap();
        let done = migrate_at(dir.path(), "legacy", "~T1").unwrap();
        assert_eq!(done, Migrated::Converted(3));
        assert!(!dir.path().join(RATCHET_LOCK_FILE).exists());
        let text = std::fs::read_to_string(dir.path().join(BASELINE_FILE)).unwrap();
        assert_eq!(Baseline::parse(&text).unwrap().key_count(), 3);
    }

    // frob:tests crates/frob/src/migrate_cmd.rs::migrate_at
    #[test]
    fn migrate_twice_leaves_the_baseline_alone() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join(RATCHET_LOCK_FILE), lock()).unwrap();
        migrate_at(dir.path(), "legacy", "~T1").unwrap();
        let before = std::fs::read_to_string(dir.path().join(BASELINE_FILE)).unwrap();
        // A lock reappearing must not overwrite the baseline.
        std::fs::write(
            dir.path().join(RATCHET_LOCK_FILE),
            format!(r#"{{"ZED002": ["{}"]}}"#, "d".repeat(64)),
        )
        .unwrap();
        assert_eq!(
            migrate_at(dir.path(), "again", "~T1").unwrap(),
            Migrated::AlreadyDone
        );
        let after = std::fs::read_to_string(dir.path().join(BASELINE_FILE)).unwrap();
        assert_eq!(before, after);
    }

    // frob:tests crates/frob/src/migrate_cmd.rs::migrate_at
    #[test]
    fn migrate_without_a_lock_is_a_no_op() {
        let dir = tempfile::tempdir().unwrap();
        assert_eq!(
            migrate_at(dir.path(), "r", "~T1").unwrap(),
            Migrated::NoLock
        );
        assert!(!dir.path().join(BASELINE_FILE).exists());
    }
}
