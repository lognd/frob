//! `rule fmt`: rewrite a rule file to the canonical layout.

use crate::grl::format_source;
use gob_text::FileInterner;

/// What formatting one file would do.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Formatted {
    /// Already canonical.
    Unchanged,
    /// The canonical text, different from the input.
    Changed(String),
    /// The file cannot be formatted (syntax errors, comments); the reason.
    Skipped(String),
}

/// Format one rule file's text.
pub fn format_text(path: &str, source: &str) -> Formatted {
    match format_source(FileInterner::new().intern(path), source) {
        Ok(text) if text == source => Formatted::Unchanged,
        Ok(text) => Formatted::Changed(text),
        Err(e) => Formatted::Skipped(e.to_string()),
    }
}
