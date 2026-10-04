//! Typed manifest errors carrying the stable rule ids PACK004 and PACK005.

use crate::limits::Owner;

/// The stable rule id of a [`PackError`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PackCode {
    /// Two packs declare one family or one name.
    Pack004,
    /// A manifest is malformed.
    Pack005,
}

impl PackCode {
    /// The id as printed, for example `PACK005`.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Pack004 => "PACK004",
            Self::Pack005 => "PACK005",
        }
    }
}

/// Why a manifest was refused or a set of packs conflicts.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum PackError {
    /// PACK005: the manifest is unreadable, unknown-keyed or out of bounds.
    #[error("PACK005 {file}{}: key `{key}`: {reason}", line_suffix(*.line))]
    Malformed {
        /// The manifest file.
        file: String,
        /// The dotted key at fault (`pack.families`), or `<file>`.
        key: String,
        /// One-based line, when the parser located it.
        line: Option<usize>,
        /// What is wrong.
        reason: String,
    },
    /// PACK004: two packs own one rule family.
    #[error("PACK004 family `{family}` is owned by both `{}` ({}) and `{}` ({})", first.name, first.file, second.name, second.file)]
    DuplicateFamily {
        /// The contested family prefix.
        family: String,
        /// The pack seen first.
        first: Owner,
        /// The pack seen second.
        second: Owner,
    },
    /// PACK004: two packs share one name.
    #[error("PACK004 pack name `{}` is declared by both {} and {}", first.name, first.file, second.file)]
    DuplicateName {
        /// The pack seen first.
        first: Owner,
        /// The pack seen second.
        second: Owner,
    },
}

fn line_suffix(line: Option<usize>) -> String {
    line.map_or_else(String::new, |l| format!(":{l}"))
}

impl PackError {
    /// The stable rule id of this error.
    pub fn code(&self) -> PackCode {
        match self {
            Self::Malformed { .. } => PackCode::Pack005,
            Self::DuplicateFamily { .. } | Self::DuplicateName { .. } => PackCode::Pack004,
        }
    }

    /// Builds a PACK005 for `key` in `file`.
    pub(crate) fn malformed(file: &str, key: &str, reason: impl Into<String>) -> Self {
        Self::Malformed {
            file: file.to_owned(),
            key: key.to_owned(),
            line: None,
            reason: reason.into(),
        }
    }
}
