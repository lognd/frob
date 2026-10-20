//! The plugin fix model (security.md 2.10, SEC-15).
//!
//! A plugin edit is (file handle, byte range, replacement text) and nothing else. The host
//! validates it against the finding's primary span and the call's subject set before it ever
//! becomes a [`crate::Fix`]; this module holds only the data and the reasons a fix is dropped.

// frob:ticket 01M3ZX7ZXZJ37A38BA4AVT0QRG

use gob_text::{FileId, TextRange};
use thiserror::Error;

use crate::meta::Applicability;

/// One edit proposed by a plugin: a handle from the subject set, a byte range, a replacement.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PluginEdit {
    /// File handle; must belong to the subject set of the call.
    pub file: FileId,
    /// Byte range replaced; must lie inside the finding's primary span.
    pub range: TextRange,
    /// Replacement text.
    pub replacement: String,
}

/// A fix as a plugin proposes it, before host validation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PluginFix {
    /// Applicability the plugin claims.
    pub applicability: Applicability,
    /// Short title (plugin-authored text).
    pub title: String,
    /// The edits.
    pub edits: Vec<PluginEdit>,
}

/// Why a plugin fix was dropped; each is reported, never silently ignored.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum FixDrop {
    /// The edit names a file outside the subject set of the call.
    #[error("edit names a file outside the subject set ({0})")]
    NotInSubjectSet(FileId),
    /// The edit's range is not inside the finding's primary span.
    #[error("edit lies outside the finding's primary span ({0})")]
    OutsidePrimarySpan(FileId),
    /// The edit touches the control plane; refused at every applicability.
    #[error("edit touches the control plane: {0}")]
    ControlPlane(String),
    /// The fix carries no edits (a manual fix cannot come from a plugin).
    #[error("fix carries no edits")]
    NoEdits,
}

/// Cap a plugin's claimed applicability: `machine` only when the pack holds `fix.machine`.
#[must_use]
pub const fn cap_applicability(claimed: Applicability, holds_fix_machine: bool) -> Applicability {
    match claimed {
        Applicability::Machine if !holds_fix_machine => Applicability::MaybeIncorrect,
        other => other,
    }
}
