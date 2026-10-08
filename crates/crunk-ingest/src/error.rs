//! Typed ingest failures.

// frob:ticket 01M43ARY91XZ35DN9SCHRHS033

use std::path::PathBuf;

/// Why an ingest could not run at all (per-file problems are diagnostics, not errors).
#[derive(Debug, thiserror::Error)]
pub enum IngestError {
    /// `css_root` exists but is not a directory.
    #[error("css root {0} exists but is not a directory")]
    CssRootNotDirectory(PathBuf),
    /// A directory walk failed before it started.
    #[error("cannot walk {path}: {source}")]
    Walk {
        /// The directory being walked.
        path: PathBuf,
        /// The walk error.
        source: gob_walk::WalkError,
    },
}
