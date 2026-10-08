//! Failures of `land` and their mapping to CLI errors.

use frob_check::CheckError;
use frob_evidence::EvidenceError;
use frob_lease::LeaseError;
use frob_ledger::LedgerError;
use gob_cli::CliError;
use gob_diagnostics::{Refusal, RefusalClass};
use gob_git::GitError;

/// Why a land did not complete.
#[derive(Debug, thiserror::Error)]
pub enum LandError {
    /// A precondition or guard refused with its own code, message and remedy.
    #[error(transparent)]
    Refused(#[from] Refusal),
    /// The ledger refused or failed.
    #[error(transparent)]
    Ledger(#[from] LedgerError),
    /// The lease store failed.
    #[error(transparent)]
    Lease(#[from] LeaseError),
    /// Git failed.
    #[error(transparent)]
    Git(#[from] GitError),
    /// The check could not run (findings are never errors).
    #[error(transparent)]
    Check(#[from] CheckError),
    /// The evidence store or guard failed.
    #[error(transparent)]
    Evidence(#[from] EvidenceError),
    /// The flags are inconsistent.
    #[error("usage: {0}")]
    Usage(String),
    /// The repository or its config cannot be used.
    #[error("E-CONFIG: {0}")]
    Config(String),
    /// A filesystem operation failed.
    #[error("E-LAND-IO: {context}: {source}")]
    Io {
        /// What was being done.
        context: String,
        /// The OS error.
        source: std::io::Error,
    },
}

impl LandError {
    /// An I/O failure with the action that hit it.
    pub fn io(context: impl Into<String>, source: std::io::Error) -> Self {
        Self::Io {
            context: context.into(),
            source,
        }
    }

    /// The refusal behind this error, when it is one.
    pub fn refusal(&self) -> Option<&Refusal> {
        match self {
            Self::Refused(r) => Some(r),
            _ => None,
        }
    }
}

/// A refusal that needs the caller to change something, with its fixing command.
pub(crate) fn needs_action(
    code: &str,
    message: impl Into<String>,
    remedy: impl Into<String>,
) -> LandError {
    LandError::Refused(
        Refusal::new(code, RefusalClass::GuardNeedsAction, message).with_remedy(remedy),
    )
}

impl From<LandError> for CliError {
    fn from(e: LandError) -> Self {
        match e {
            LandError::Refused(r) => r.into(),
            LandError::Ledger(l) => match l.to_refusal() {
                Some(r) => r.into(),
                None => Self::internal(l),
            },
            LandError::Lease(l) => l.into(),
            LandError::Usage(m) => Self::Usage(m),
            LandError::Config(m) => Refusal::new("E-CONFIG", RefusalClass::GuardNeedsAction, m)
                .with_remedy("fix frob.toml as described, then rerun")
                .into(),
            LandError::Check(c) => Self::internal(c),
            LandError::Git(g @ GitError::Rev { .. }) => {
                Refusal::new("E-LAND-GIT-REV", RefusalClass::GuardNeedsAction, g.to_string())
                    .with_remedy("check that the base branch and the ticket branch exist (git branch --list), then rerun frob land")
                    .into()
            }
            LandError::Git(g) => Self::internal(g),
            LandError::Evidence(v) => Self::internal(v),
            LandError::Io { context, source } => Self::internal(format!("{context}: {source}")),
        }
    }
}
