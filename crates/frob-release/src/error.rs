//! Typed, teaching errors for the changelog compile.

use std::path::PathBuf;

use crate::fragment::Kind;

/// One problem with one fragment file; the message names the file and the remedy.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum FragmentError {
    /// The file name is not `<ulid>.<type>.md`.
    #[error(
        "changelog.d/{file}: name must be `<ulid>.<type>.md` ({why}); rename it, e.g. `frob ticket show` gives the ULID"
    )]
    BadName {
        /// File name inside changelog.d.
        file: String,
        /// What is wrong with the name.
        why: String,
    },
    /// The type segment is not one of the known types.
    #[error(
        "changelog.d/{file}: unknown type `{got}`; valid types are {}",
        Kind::valid_list()
    )]
    UnknownType {
        /// File name inside changelog.d.
        file: String,
        /// The type segment found.
        got: String,
    },
    /// The ULID does not resolve to a ticket in the ledger.
    #[error(
        "changelog.d/{file}: ULID {ulid} is not a ticket in the ledger; name the fragment after the ticket that shipped the change"
    )]
    UnknownTicket {
        /// File name inside changelog.d.
        file: String,
        /// The ULID that did not resolve.
        ulid: String,
    },
    /// The body has no text.
    #[error(
        "changelog.d/{file}: empty fragment; write one or two user-facing sentences, optionally prefixed `frob:`"
    )]
    Empty {
        /// File name inside changelog.d.
        file: String,
    },
    /// The body has a non-ASCII character.
    #[error(
        "changelog.d/{file}: non-ASCII character at byte {at}; this repository is ASCII only, rewrite it"
    )]
    NonAscii {
        /// File name inside changelog.d.
        file: String,
        /// Byte offset of the first offender.
        at: usize,
    },
    /// The file could not be read.
    #[error("changelog.d/{file}: cannot read ({reason})")]
    Unreadable {
        /// File name inside changelog.d.
        file: String,
        /// The I/O failure text.
        reason: String,
    },
}

/// Why `frob release changelog` refused or failed.
#[derive(Debug, thiserror::Error)]
pub enum ReleaseError {
    /// One or more fragments are invalid (all are listed).
    #[error("{} invalid changelog fragment(s):\n{}", .0.len(), lines(.0))]
    Fragments(Vec<FragmentError>),
    /// The version is not `MAJOR.MINOR.PATCH` with an optional `-pre`.
    #[error("invalid version `{0}`; use MAJOR.MINOR.PATCH, e.g. 0.532.0")]
    InvalidVersion(String),
    /// The date is not `YYYY-MM-DD`.
    #[error("invalid date `{0}`; use YYYY-MM-DD")]
    InvalidDate(String),
    /// CHANGELOG.md already has a section for this version.
    #[error(
        "CHANGELOG.md already has a section for {0}; pick the next version or restore the file"
    )]
    VersionExists(String),
    /// A compiled section no longer matches its integrity marker.
    #[error(
        "CHANGELOG.md section {0} was edited by hand; restore it from git, or fix the fragment and recompile (compiled sections are never hand-edited)"
    )]
    Tampered(String),
    /// A section after the header has no integrity marker.
    #[error(
        "CHANGELOG.md section `{0}` has no integrity marker; only compiled sections may follow the header (older history lives in CHANGELOG-v1.md)"
    )]
    Unmarked(String),
    /// A file operation failed.
    #[error("{op} {}: {reason}", path.display())]
    Io {
        /// What was attempted.
        op: &'static str,
        /// The path involved.
        path: PathBuf,
        /// The I/O failure text.
        reason: String,
    },
}

fn lines(errs: &[FragmentError]) -> String {
    errs.iter()
        .map(|e| format!("  {e}"))
        .collect::<Vec<_>>()
        .join("\n")
}
