//! The typed errors of frob-pm; every message starts with its stable `E-PM-*` code.

use frob_ledger::LedgerError;

use crate::model::ObjectKind;

/// Everything that can go wrong reading, folding or writing a milestone or cycle.
#[derive(Debug, thiserror::Error)]
pub enum PmError {
    /// The ledger (git, store) failed underneath.
    #[error("E-PM-LEDGER: {0}")]
    Ledger(#[from] LedgerError),
    /// An object file or event file cannot be parsed or rendered.
    #[error("E-PM-FORMAT: {path}: {message}")]
    Malformed {
        /// Repo-relative path or a label.
        path: String,
        /// What is wrong.
        message: String,
    },
    /// The events of one object cannot be folded into a state.
    #[error("E-PM-FOLD: {kind} {id}: {message}")]
    Fold {
        /// Milestone or cycle.
        kind: ObjectKind,
        /// Full ULID of the object.
        id: String,
        /// What is wrong.
        message: String,
    },
    /// The request breaks a model rule (bad date range, wrong state for the kind, ...).
    #[error("E-PM-INPUT: {0}")]
    Invalid(String),
    /// No object matches the reference.
    #[error("E-PM-NOTFOUND: no {kind} matches `{reference}`")]
    NotFound {
        /// Milestone or cycle.
        kind: ObjectKind,
        /// The reference as given.
        reference: String,
    },
    /// The reference matches more than one object.
    #[error("E-PM-AMBIGUOUS: `{reference}` matches {count} {kind}s")]
    Ambiguous {
        /// Milestone or cycle.
        kind: ObjectKind,
        /// The reference as given.
        reference: String,
        /// How many matched.
        count: usize,
    },
}

impl PmError {
    /// A [`PmError::Malformed`] for `path`.
    pub fn malformed(path: impl Into<String>, message: impl Into<String>) -> Self {
        Self::Malformed {
            path: path.into(),
            message: message.into(),
        }
    }

    /// A [`PmError::Invalid`].
    pub fn invalid(message: impl Into<String>) -> Self {
        Self::Invalid(message.into())
    }
}

/// Result alias of this crate.
pub type Result<T> = std::result::Result<T, PmError>;
