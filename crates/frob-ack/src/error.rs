//! The error set of this crate and its mapping to CLI errors.

use std::path::PathBuf;

use gob_cli::{CliError, Refusal, RefusalClass};
use gob_git::GitError;
use gob_lock::{LockError, PlanError};
use gob_symbols::ResolveError;

/// Why collecting inputs, acking or querying failed.
#[derive(Debug, thiserror::Error)]
pub enum AckError {
    /// The repository walk failed.
    #[error("E-ACK-WALK: {0}")]
    Walk(#[from] gob_walk::WalkError),
    /// `frob.lock` could not be read, parsed or written.
    #[error(transparent)]
    Lock(#[from] LockError),
    /// A git operation failed.
    #[error(transparent)]
    Git(#[from] GitError),
    /// A target names no symbol, or several.
    #[error("E-ACK-RESOLVE: `{input}`: {source}")]
    Resolve {
        /// What the caller typed.
        input: String,
        /// Why it did not resolve.
        source: ResolveError,
    },
    /// The ack could not be planned: empty selection, or a stale lock not yet migrated.
    #[error(transparent)]
    Plan(#[from] PlanError),
    /// The checkout has no branch to commit `frob.lock` on.
    #[error("E-ACK-DETACHED: HEAD is detached; check out a branch before acking")]
    DetachedHead,
    /// A file could not be read.
    #[error("E-ACK-IO: read {path}: {source}")]
    Io {
        /// The file.
        path: PathBuf,
        /// The OS error.
        source: std::io::Error,
    },
}

impl From<AckError> for CliError {
    fn from(e: AckError) -> Self {
        match &e {
            AckError::Resolve { .. } | AckError::Plan(_) => Self::Usage(e.to_string()),
            AckError::DetachedHead => Refusal::new(
                "E-ACK-DETACHED",
                RefusalClass::GuardNeedsAction,
                e.to_string(),
            )
            .with_remedy("git switch <branch>")
            .into(),
            AckError::Git(
                g @ (GitError::LocalEdits { .. }
                | GitError::NoIdentity
                | GitError::CasExhausted { .. }),
            ) => {
                let class = if matches!(g, GitError::CasExhausted { .. }) {
                    RefusalClass::GuardRetryByWaiting
                } else {
                    RefusalClass::GuardNeedsAction
                };
                Refusal::new(g.code(), class, g.to_string()).into()
            }
            _ => Self::internal(e),
        }
    }
}
