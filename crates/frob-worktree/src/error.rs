//! Failures of `work`, `start` and `requeue` and their mapping to CLI errors.

use std::path::PathBuf;

use frob_lease::LeaseError;
use frob_ledger::LedgerError;
use gob_cli::CliError;
use gob_diagnostics::{Refusal, RefusalClass};
use gob_git::GitError;

/// Why a worktree verb did not complete.
#[derive(Debug, thiserror::Error)]
pub enum WorktreeError {
    /// The ledger refused or failed.
    #[error(transparent)]
    Ledger(#[from] LedgerError),
    /// The lease store failed (a held lease arrives as [`WorktreeError::Refused`]).
    #[error(transparent)]
    Lease(#[from] LeaseError),
    /// Git failed creating the worktree or merging the base.
    #[error(transparent)]
    Git(#[from] GitError),
    /// A guard refused with its own code, message and remedy.
    #[error(transparent)]
    Refused(#[from] Refusal),
    /// The worktree path is taken by something that is not this ticket's worktree.
    #[error("E-WORKTREE-EXISTS: {} exists and is not a git worktree", .0.display())]
    PathExists(PathBuf),
    /// The flags are inconsistent.
    #[error("usage: {0}")]
    Usage(String),
    /// The config could not be read.
    #[error("E-CONFIG: {0}")]
    Config(String),
}

impl WorktreeError {
    /// A `E-TICKET-NOT-WORKABLE` refusal with the command that fixes it, when there is one.
    pub fn not_workable(message: impl Into<String>, remedy: Option<String>) -> Self {
        let r = Refusal::new(
            "E-TICKET-NOT-WORKABLE",
            RefusalClass::GuardNeedsAction,
            message,
        );
        Self::Refused(match remedy {
            Some(c) => r.with_remedy(c),
            None => r,
        })
    }
}

impl From<WorktreeError> for CliError {
    fn from(e: WorktreeError) -> Self {
        match e {
            WorktreeError::Ledger(l) => match l.to_refusal() {
                Some(r) => r.into(),
                None => Self::internal(l),
            },
            WorktreeError::Lease(l) => l.into(),
            WorktreeError::Git(g) => Self::internal(g),
            WorktreeError::Refused(r) => r.into(),
            WorktreeError::PathExists(p) => Refusal::new(
                "E-WORKTREE-EXISTS",
                RefusalClass::GuardNeedsAction,
                format!("{} exists and is not a git worktree", p.display()),
            )
            .with_remedy("frob work <ticket> --worktree <another path>")
            .into(),
            WorktreeError::Usage(m) => Self::Usage(m),
            WorktreeError::Config(m) => Refusal::new("E-CONFIG", RefusalClass::GuardNeedsAction, m)
                .with_remedy("fix frob.toml as described, then rerun")
                .into(),
        }
    }
}
