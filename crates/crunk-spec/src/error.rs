//! Typed load errors for `crunk.toml`, each with a stable code, an exit code and a location.

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

use std::path::PathBuf;

use gob_config::ConfigError;
use gob_diagnostics::{ExitCode, RefusalClass};

/// Which way loading `crunk.toml` failed (the Python `SpecError` kinds).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SpecErrorKind {
    /// No readable `crunk.toml` at the stated path.
    Missing,
    /// The file is not valid TOML.
    Malformed,
    /// The file is valid TOML but violates the design spec schema.
    Invalid,
}

/// Where in the file a problem sits, 1-based.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Location {
    /// 1-based line.
    pub line: usize,
    /// 1-based column in characters.
    pub column: usize,
}

/// Why `crunk.toml` could not be turned into a [`crate::DesignSpec`].
#[derive(Debug, Clone, PartialEq, thiserror::Error)]
pub enum SpecError {
    /// No readable `crunk.toml` at the stated path.
    #[error("crunk.toml not found at {}{}", path.display(), reason_text(reason.as_deref()))]
    Missing {
        /// The path that was tried.
        path: PathBuf,
        /// Why the file could not be read, when it exists but is unreadable.
        reason: Option<String>,
    },
    /// The file is not valid TOML.
    #[error("{}{}: malformed TOML: {message}", path.display(), at_text(*at))]
    Malformed {
        /// File involved.
        path: PathBuf,
        /// Where the parser stopped, when known.
        at: Option<Location>,
        /// Parser message.
        message: String,
    },
    /// The file is valid TOML but violates the schema.
    #[error("{}{}: {detail}{}", path.display(), at_text(*at), suggestion_text(suggestion.as_deref()))]
    Invalid {
        /// File involved.
        path: PathBuf,
        /// Where the offending key or value sits, when known.
        at: Option<Location>,
        /// What is wrong, naming the section and key as `[section].key: ...`.
        detail: String,
        /// The offending key when the problem is an unknown key.
        key: Option<String>,
        /// Nearest valid key by edit distance, for an unknown key.
        suggestion: Option<String>,
    },
}

impl SpecError {
    /// The failure kind.
    pub const fn kind(&self) -> SpecErrorKind {
        match self {
            Self::Missing { .. } => SpecErrorKind::Missing,
            Self::Malformed { .. } => SpecErrorKind::Malformed,
            Self::Invalid { .. } => SpecErrorKind::Invalid,
        }
    }

    /// Stable refusal code: `E-NO-CONFIG` for a missing file, `E-CONFIG` otherwise.
    pub const fn code(&self) -> &'static str {
        match self {
            Self::Missing { .. } => "E-NO-CONFIG",
            Self::Malformed { .. } | Self::Invalid { .. } => "E-CONFIG",
        }
    }

    /// Refusal class: input that fails its schema is a usage error, a missing file needs action.
    pub const fn class(&self) -> RefusalClass {
        match self {
            Self::Missing { .. } => RefusalClass::GuardNeedsAction,
            Self::Malformed { .. } | Self::Invalid { .. } => RefusalClass::UsageError,
        }
    }

    /// Process exit code: 2 for a malformed or invalid file, 3 for a missing one.
    pub const fn exit_code(&self) -> ExitCode {
        self.class().exit_code()
    }

    /// Where the problem sits in the file, when the loader could tell.
    pub const fn location(&self) -> Option<Location> {
        match self {
            Self::Missing { .. } => None,
            Self::Malformed { at, .. } | Self::Invalid { at, .. } => *at,
        }
    }

    /// The offending key of an unknown-key error.
    pub fn key(&self) -> Option<&str> {
        match self {
            Self::Invalid { key, .. } => key.as_deref(),
            _ => None,
        }
    }

    /// The did-you-mean suggestion of an unknown-key error.
    pub fn suggestion(&self) -> Option<&str> {
        match self {
            Self::Invalid { suggestion, .. } => suggestion.as_deref(),
            _ => None,
        }
    }
}

impl SpecError {
    /// This failure as the shared [`ConfigError`] a check run reports, naming the offending table
    /// and key the way a `frob.toml` error does; the location is kept in the message.
    pub fn into_config_error(self) -> ConfigError {
        match self {
            Self::Missing { path, reason } => ConfigError::Io {
                path: path.clone(),
                source: std::io::Error::new(
                    std::io::ErrorKind::NotFound,
                    reason.unwrap_or_else(|| format!("{} not found", path.display())),
                ),
            },
            Self::Malformed { path, at, message } => ConfigError::Parse {
                message: format!("{}{}", message, at_text(at)),
                path,
            },
            Self::Invalid {
                key: Some(key),
                suggestion,
                detail,
                ..
            } => {
                let table = detail
                    .strip_prefix('[')
                    .and_then(|rest| rest.split_once(']'))
                    .map_or_else(|| "crunk.toml".to_owned(), |(sec, _)| sec.to_owned());
                ConfigError::UnknownKey {
                    table,
                    key,
                    suggestion,
                }
            }
            Self::Invalid {
                path, at, detail, ..
            } => {
                let (table, message) = match detail
                    .strip_prefix('[')
                    .and_then(|rest| rest.split_once("]: "))
                {
                    Some((sec, rest)) => (sec.to_owned(), rest.to_owned()),
                    None => ("crunk.toml".to_owned(), detail),
                };
                ConfigError::Invalid {
                    table,
                    message: format!("{}{}: {message}", path.display(), at_text(at)),
                }
            }
        }
    }
}

fn reason_text(reason: Option<&str>) -> String {
    reason.map_or_else(String::new, |r| format!(" ({r})"))
}

fn at_text(at: Option<Location>) -> String {
    at.map_or_else(String::new, |l| format!(":{}:{}", l.line, l.column))
}

fn suggestion_text(suggestion: Option<&str>) -> String {
    suggestion.map_or_else(String::new, |s| format!("; did you mean `{s}`?"))
}
