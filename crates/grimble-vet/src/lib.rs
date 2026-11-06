//! Dependency vetting (cli.md `grimble vet`, boundaries.md 2.3): the `Cargo.lock` delta between a
//! base and a head, an allowlist of vetted crates, an offline `RustSec` advisory snapshot and
//! duplicate-version detection.
//!
//! Pure over text: the caller reads the lockfiles (from git or disk) and the snapshot directory.
//! Licence, yanked and maintenance checks read an exported registry metadata file ([`meta`]);
//! typosquat detection compares names with a built-in list of popular crates ([`typosquat`]).

// frob:ticket 01M406M2HX6Z6SEGM6HRPQKHAV

pub mod advisory;
pub mod hook;
pub mod host;
pub mod lockfile;
pub mod meta;
pub mod pass;
pub mod rules;
pub mod typosquat;
pub mod vet;

pub use advisory::{Advisory, RefreshReport, Snapshot, refresh, stamp_as_of};
pub use hook::{InstallRequest, parse_install, vet_command};
pub use host::VetHost;
pub use lockfile::{Package, examined, parse_lockfile};
pub use meta::Meta;
pub use pass::{VetInput, VetPassReport, analyze};
pub use vet::{Allowlist, Finding, Rule, Severity, VetReport, vet, vet_with_meta};

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
