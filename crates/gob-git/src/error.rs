//! Error type with one stable `E-GIT-*` code per variant.

use std::path::PathBuf;

/// Everything `gob-git` can fail with; the payloads are rendered strings so
/// the enum stays small and does not leak gix's error types.
#[derive(Debug, thiserror::Error)]
pub enum GitError {
    /// No repository found at or above the given directory.
    #[error("E-GIT-DISCOVER: no git repository at or above {}: {detail}", path.display())]
    Discover {
        /// Directory the search started from.
        path: PathBuf,
        /// Underlying failure.
        detail: String,
    },
    /// A revision spec or ref name did not resolve.
    #[error("E-GIT-REV: cannot resolve `{spec}`: {detail}")]
    Rev {
        /// The spec that failed.
        spec: String,
        /// Underlying failure.
        detail: String,
    },
    /// Reading or writing the object database failed.
    #[error("E-GIT-ODB: {0}")]
    Odb(String),
    /// A ref read or transaction failed for a reason other than a lost race.
    #[error("E-GIT-REF: {0}")]
    Ref(String),
    /// Reading or writing the index failed.
    #[error("E-GIT-INDEX: {0}")]
    Index(String),
    /// Status or diff computation failed.
    #[error("E-GIT-STATUS: {0}")]
    Status(String),
    /// A filesystem operation failed.
    #[error("E-GIT-IO: {context}: {source}")]
    Io {
        /// What was being done.
        context: String,
        /// The OS error.
        source: std::io::Error,
    },
    /// The compare-and-swap ref update lost the race on every attempt.
    #[error(
        "E-GIT-CAS-EXHAUSTED: ref {ref_name} kept moving after {attempts} attempts; retry the verb"
    )]
    CasExhausted {
        /// The ref that kept changing.
        ref_name: String,
        /// Attempts made (retries + 1).
        attempts: u32,
    },
    /// A path given to a ledger write is not a clean repo-relative path.
    #[error("E-GIT-PATH: invalid repo-relative path `{0}`")]
    BadPath(String),
    /// No author identity was given and git config has none.
    #[error("E-GIT-IDENTITY: no author; set user.name and user.email in git config")]
    NoIdentity,
    /// The checked-out ref has local edits on a path the ledger must update.
    #[error(
        "E-GIT-LOCAL-EDITS: `{path}` has local edits in this checkout; commit or stash them, then retry"
    )]
    LocalEdits {
        /// The conflicting repo-relative path.
        path: String,
    },
    /// The requested comparison or operation is not supported.
    #[error("E-GIT-UNSUPPORTED: {0}")]
    Unsupported(String),
    /// A spawn fallback could not run or exited non-zero.
    #[error("E-GIT-SPAWN: git {args}: {detail}")]
    Spawn {
        /// The git arguments.
        args: String,
        /// Failure description including captured stderr.
        detail: String,
    },
}

impl GitError {
    /// The stable `E-GIT-*` code of this error, for machine consumers.
    pub fn code(&self) -> &'static str {
        match self {
            Self::Discover { .. } => "E-GIT-DISCOVER",
            Self::Rev { .. } => "E-GIT-REV",
            Self::Odb(_) => "E-GIT-ODB",
            Self::Ref(_) => "E-GIT-REF",
            Self::Index(_) => "E-GIT-INDEX",
            Self::Status(_) => "E-GIT-STATUS",
            Self::Io { .. } => "E-GIT-IO",
            Self::CasExhausted { .. } => "E-GIT-CAS-EXHAUSTED",
            Self::BadPath(_) => "E-GIT-PATH",
            Self::NoIdentity => "E-GIT-IDENTITY",
            Self::LocalEdits { .. } => "E-GIT-LOCAL-EDITS",
            Self::Unsupported(_) => "E-GIT-UNSUPPORTED",
            Self::Spawn { .. } => "E-GIT-SPAWN",
        }
    }

    /// Wrap an I/O error with what was being attempted.
    pub(crate) fn io(context: impl Into<String>, source: std::io::Error) -> Self {
        Self::Io {
            context: context.into(),
            source,
        }
    }
}
