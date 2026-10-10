//! Scope leases: who may write which files (tickets.md section 3, decision D26).
// frob:ticket 01M4H6M6DYW002R049JG7AD7YA
//!
//! A lease is `<common_dir>/frob/leases/<ticket ulid>.toml` holding the ticket,
//! its [`Holder`] (actor plus worktree path), the scope globs, timestamps and
//! TTL, and the history of takeovers. Every read-decide-write sequence runs
//! under one lock file (`<common_dir>/frob/leases.lock`, see [`store`]), so two
//! concurrent `work` calls on overlapping tickets produce exactly one lease.
//! Overlap is glob-text intersection OR resolved-file-set intersection
//! ([`overlap`]); files in `[lease] shared_files` are exempt. Leases are
//! single-clone: other clones see only the ledger CAS and rule [`Scope001`].
//!
//! Entry points: [`LeaseStore`] (acquire, renew, rescope, release, steal, list,
//! contention), [`LeaseGuard`] (the [`LeaseCheck`](frob_ledger::guards::LeaseCheck)
//! for `ticket doable`), [`scope001`], and [`register`] for the `lease list` and
//! `lease list --contention` verbs.

pub mod config;
pub mod error;
pub mod guard;
pub mod model;
pub mod overlap;
pub mod rule;
pub mod store;
pub mod unmatched;
pub mod verbs;

use std::path::{Path, PathBuf};

pub use config::LeaseConfig;
pub use error::LeaseError;
pub use guard::LeaseGuard;
pub use model::{Holder, Lease, StealRecord};
pub use rule::{Scope001, scope001};
pub use store::{Acquired, Contended, CorruptLease, LeaseStore, Stolen};

/// Open the lease store of the repository containing `cwd` with the caller's `cfg`.
///
/// Every verb passes the same [`LeaseConfig`] (built once from the materialized
/// `[lease]` table) so they agree on `shared_files`. Returns the store and the work tree root.
///
/// # Errors
///
/// [`LeaseError::Repo`] when `cwd` is not inside a git work tree, or
/// [`LeaseError::BadGlob`] when `cfg.shared_files` holds an invalid glob.
pub fn open_store(
    cwd: &Path,
    cfg: LeaseConfig,
    clock: std::sync::Arc<dyn gob_time::Clock>,
) -> Result<(LeaseStore, PathBuf), LeaseError> {
    let repo = gob_git::Repo::discover(cwd).map_err(|e| LeaseError::Repo(e.to_string()))?;
    let root = repo.work_dir().map(Path::to_path_buf).ok_or_else(|| {
        LeaseError::Repo(format!("{} is not inside a git work tree", cwd.display()))
    })?;
    tracing::debug!(root = %root.display(), shared = cfg.shared_files.len(), "opening lease store");
    Ok((LeaseStore::open(&repo, cfg, clock)?, root))
}

/// Open the lease store of `cwd` with `[lease]` loaded from its `frob.toml`.
///
/// For verbs that live outside the `frob` binary and so cannot see `FrobConfig`.
///
/// # Errors
///
/// [`LeaseError::Repo`] when `cwd` is not in a work tree or the config is invalid.
pub fn open_store_from_file(
    cwd: &Path,
    clock: std::sync::Arc<dyn gob_time::Clock>,
) -> Result<(LeaseStore, PathBuf), LeaseError> {
    let repo = gob_git::Repo::discover(cwd).map_err(|e| LeaseError::Repo(e.to_string()))?;
    let root = repo.work_dir().map(Path::to_path_buf).ok_or_else(|| {
        LeaseError::Repo(format!("{} is not inside a git work tree", cwd.display()))
    })?;
    let cfg = LeaseConfig::load(&root).map_err(|e| LeaseError::Repo(e.to_string()))?;
    open_store(cwd, cfg, clock)
}

/// Best-effort heartbeat: renew the live lease held from the worktree containing `cwd`.
///
/// Called by verbs that prove agent activity (evidence add, check, test) so a
/// long run stays inside the TTL without an explicit command; failures are
/// logged, never surfaced, and a clone without leases is a no-op.
pub fn heartbeat(cwd: &Path, clock: std::sync::Arc<dyn gob_time::Clock>) {
    let (store, root) = match open_store_from_file(cwd, clock) {
        Ok(opened) => opened,
        Err(e) => {
            tracing::debug!(error = %e, "heartbeat skipped: no lease store");
            return;
        }
    };
    match store.renew_for_worktree(&root) {
        Ok(renewed) => tracing::debug!(count = renewed.len(), root = %root.display(), "heartbeat"),
        Err(e) => tracing::warn!(error = %e, "heartbeat failed"),
    }
}

/// Register `lease list` and the hidden `ticket contention` alias on a product root.
pub fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<verbs::LeaseList>()
        .register::<verbs::Contention>()
}
