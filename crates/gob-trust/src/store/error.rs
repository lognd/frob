//! Typed errors for the trust store.

use crate::error::TrustError;

/// Why a trust-store operation failed.
#[derive(Debug, thiserror::Error)]
pub enum StoreError {
    /// Key, path or filesystem trouble.
    #[error(transparent)]
    Trust(#[from] TrustError),
    /// A field cannot be stored (control characters or a non-UTF-8 path).
    #[error("trust field {0} cannot be stored: it must be single-line text")]
    BadField(&'static str),
}
