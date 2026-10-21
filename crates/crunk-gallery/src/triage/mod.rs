//! Triage: review rendered cells in a local contact sheet and save verdicts to the manifest.
//!
//! `triage` is the third step of `enumerate -> render -> triage -> check`. [`store`] reads and
//! writes the manifest (always as v3, with attributed, optionally expiring verdicts) and merges a
//! render run into it. [`server`] is a tiny blocking HTTP server on `127.0.0.1` that serves the
//! contact sheet ([`page`]) and records keyboard verdicts; it needs no async runtime, so
//! `tokio` stays confined to the serve crates (boundaries.md section 6).
//!
//! The server is a local, single-user tool and defends itself accordingly: it binds loopback
//! only, every request must carry the random per-run token, the `Host` header must name the
//! loopback address (DNS rebinding) and a cross-origin `POST` is refused.

// frob:ticket 01M43ATE06MNRNVJJ314KW24RJ

pub mod page;
pub mod server;
pub mod store;

/// Why a triage step failed.
#[derive(Debug, thiserror::Error)]
pub enum TriageError {
    /// Reading or writing the manifest or an image failed.
    #[error("triage I/O failed: {0}")]
    Io(#[from] std::io::Error),
    /// The existing manifest did not parse.
    #[error(transparent)]
    Manifest(#[from] crate::manifest::ManifestError),
    /// The verdict names a cell the gallery does not have, or is otherwise unusable.
    #[error("{0}")]
    Invalid(String),
}
