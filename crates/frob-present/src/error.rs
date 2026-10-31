//! Error type for presenter output.

use std::fmt;

/// Why a presenter could not render.
#[derive(Debug)]
pub enum PresentError {
    /// The injected writer failed.
    Write(std::io::Error),
    /// The presenter's internal lock was poisoned by a panic in another thread.
    Poisoned,
}

impl fmt::Display for PresentError {
    /// Human text for the failure.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Write(e) => write!(f, "presenter write failed: {e}"),
            Self::Poisoned => write!(f, "presenter state lock poisoned"),
        }
    }
}

impl std::error::Error for PresentError {
    /// The underlying io error, when there is one.
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Write(e) => Some(e),
            Self::Poisoned => None,
        }
    }
}

impl From<std::io::Error> for PresentError {
    /// Wrap a writer failure.
    fn from(e: std::io::Error) -> Self {
        Self::Write(e)
    }
}
