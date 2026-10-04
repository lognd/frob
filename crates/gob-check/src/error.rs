//! Failures of a check run that stop it (findings are never errors).

use gob_config::ConfigError;
use gob_walk::WalkError;

/// Why [`crate::run`] could not produce a report.
#[derive(Debug, thiserror::Error)]
pub enum CheckError {
    /// A product config table (`frob.toml`, `grimble.toml`) failed to load.
    #[error("E-CHECK-CONFIG: {0}")]
    Config(#[from] ConfigError),
    /// The repository walk failed (bad exclude glob).
    #[error("E-CHECK-WALK: {0}")]
    Walk(#[from] WalkError),
    /// The product's lock file (`frob.lock`) is malformed.
    #[error("E-CHECK-LOCK: {0}")]
    Lock(#[from] gob_lock::LockError),
    /// `--only` named neither a rule family nor a rule id.
    #[error("E-CHECK-ONLY: `{0}` is neither a rule family nor a rule id")]
    UnknownFamily(String),
    /// `--ticket` needs a git repository with a ticket ledger.
    #[error("E-CHECK-NO-LEDGER: {0}")]
    NoLedger(String),
    /// `--ticket` named no ticket of the ledger.
    #[error("E-CHECK-TICKET: {0}")]
    Ticket(String),
    /// `--fix` was requested without `--ticket` while `[check] fix_requires_scope` is true.
    #[error(
        "E-CHECK-FIX-SCOPE: `--fix` needs `--ticket` because [check] fix_requires_scope is true"
    )]
    FixNeedsScope,
    /// A fix could not be applied; the message leads with its code `E-CHECK-FIX-IO`.
    #[error("{0}")]
    FixIo(String),
    /// A file changed between the check and `--fix`, so its fix offsets are void; the path.
    #[error("E-FIX-STALE: {0} changed since the check")]
    FixStale(String),
}
