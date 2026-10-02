//! The error type of the evidence crate and its mapping to CLI refusals.

use gob_cli::{CliError, Refusal, RefusalClass};

/// Everything evidence capture, storage and lookup can fail with.
#[derive(Debug, thiserror::Error)]
pub enum EvidenceError {
    /// The `command` provider was asked to run a tool outside `[evidence] allowed_tools`.
    #[error("E-EVIDENCE-TOOL: `{tool}` is not in [evidence] allowed_tools")]
    ToolNotAllowed {
        /// The rejected program name.
        tool: String,
    },
    /// The `command` or `nextest` reference was empty or could not be split.
    #[error("E-EVIDENCE-REF: {0}")]
    BadReference(String),
    /// A provider name is not one of `nextest`, `command`, `file`.
    #[error("E-EVIDENCE-PROVIDER: `{0}` is not a provider; expected nextest, command or file")]
    BadProvider(String),
    /// An acceptance index is zero or beyond the ticket's criteria.
    #[error("E-EVIDENCE-ACCEPTS: {0}")]
    BadAccepts(String),
    /// The evidence index of `fetch` does not exist.
    #[error("E-EVIDENCE-INDEX: {0}")]
    BadIndex(String),
    /// The working directory is not inside a git work tree.
    #[error("E-NOT-A-REPO: {0} is not inside a git work tree")]
    NotARepo(String),
    /// A configured knob is unusable.
    #[error("E-EVIDENCE-CONFIG: {0}")]
    Config(String),
    /// A process could not be started or supervised.
    #[error(transparent)]
    Exec(#[from] gob_exec::ExecError),
    /// The ledger refused or failed.
    #[error(transparent)]
    Ledger(#[from] frob_ledger::LedgerError),
    /// A git read or write failed.
    #[error(transparent)]
    Git(#[from] gob_git::GitError),
    /// A file could not be read or written.
    #[error("E-EVIDENCE-IO: {path}: {source}")]
    Io {
        /// The path involved.
        path: String,
        /// The OS error.
        #[source]
        source: std::io::Error,
    },
    /// An evidence event file is not in the expected shape.
    #[error("E-EVIDENCE-FORMAT: {0}")]
    Malformed(String),
}

impl EvidenceError {
    /// Wrap an I/O failure with the path it concerns.
    pub fn io(path: impl AsRef<std::path::Path>, source: std::io::Error) -> Self {
        Self::Io {
            path: path.as_ref().display().to_string(),
            source,
        }
    }

    /// The CLI error: a refusal when the caller can fix it, else internal.
    pub fn into_cli(self) -> CliError {
        use RefusalClass::{GuardNeedsAction, UsageError};
        let refusal = match &self {
            Self::ToolNotAllowed { tool } => Some(
                Refusal::new("E-EVIDENCE-TOOL", GuardNeedsAction, self.to_string()).with_remedy(
                    format!("add \"{tool}\" to [evidence] allowed_tools in frob.toml"),
                ),
            ),
            Self::BadReference(_) | Self::BadProvider(_) | Self::BadAccepts(_) => {
                Some(Refusal::new(code_of(&self), UsageError, self.to_string()))
            }
            Self::BadIndex(_) => Some(
                Refusal::new("E-EVIDENCE-INDEX", GuardNeedsAction, self.to_string())
                    .with_remedy("frob ticket evidence list <ticket>"),
            ),
            Self::NotARepo(_) => Some(
                Refusal::new("E-NOT-A-REPO", GuardNeedsAction, self.to_string())
                    .with_remedy("git init"),
            ),
            Self::Config(_) => Some(
                Refusal::new("E-EVIDENCE-CONFIG", GuardNeedsAction, self.to_string())
                    .with_remedy("fix the [evidence] table in frob.toml"),
            ),
            Self::Ledger(e) => e.to_refusal(),
            Self::Git(_) | Self::Exec(_) | Self::Io { .. } | Self::Malformed(_) => None,
        };
        match refusal {
            Some(r) => r.into(),
            None => CliError::internal(self),
        }
    }
}

fn code_of(e: &EvidenceError) -> &'static str {
    match e {
        EvidenceError::BadReference(_) => "E-EVIDENCE-REF",
        EvidenceError::BadProvider(_) => "E-EVIDENCE-PROVIDER",
        _ => "E-EVIDENCE-ACCEPTS",
    }
}

/// The result type of this crate.
pub type Result<T> = std::result::Result<T, EvidenceError>;
