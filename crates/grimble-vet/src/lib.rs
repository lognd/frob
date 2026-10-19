//! Dependency vetting (cli.md `grimble vet`, boundaries.md 2.3): the `Cargo.lock` delta between a
//! base and a head, an allowlist of vetted crates, an offline `RustSec` advisory snapshot and
//! duplicate-version detection.
//!
//! Pure over text: the caller reads the lockfiles (from git or disk) and the snapshot directory.
//! Not yet covered (tracked as tickets): licence, yanked, maintenance signals, typosquat and the
//! `--hook` pre-install mode.

// frob:ticket 01M406M2HX6Z6SEGM6HRPQKHAV

pub mod advisory;
pub mod lockfile;
pub mod vet;

pub use advisory::{Advisory, Snapshot};
pub use lockfile::{Package, parse_lockfile};
pub use vet::{Allowlist, Finding, Rule, Severity, VetReport, vet};

/// Failure reading vetting inputs.
#[derive(Debug, thiserror::Error)]
pub enum VetError {
    /// A lockfile, allowlist or advisory was not valid TOML or lacked a required key.
    #[error("{what}: {message}")]
    Parse {
        /// What was being parsed (a file name or `Cargo.lock`).
        what: String,
        /// The parser's message.
        message: String,
    },
    /// The snapshot directory could not be read.
    #[error("cannot read {path}: {message}")]
    Io {
        /// The path that failed.
        path: String,
        /// The OS message.
        message: String,
    },
}
