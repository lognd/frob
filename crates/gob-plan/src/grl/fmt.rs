//! The `rule fmt` engine: GRL source text to canonical source text (grl-spec.md section 11).
//!
//! Library level only: it parses, refuses text it cannot format safely, and hands the tree to the
//! one canonical printer ([`super::print()`]). The verb that reads and writes files is wired in
//! the verbs ticket (~QMW7215).

// frob:ticket 01M3ZX7DG5711ZSC4R0Y64C78A
use gob_text::FileId;

use super::{ParseError, lex, parse, print};

/// Why a source text was not formatted.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum FormatError {
    /// The text has syntax errors; formatting a broken file would hide them.
    #[error("{} syntax error(s); fix them before formatting", .0.len())]
    Syntax(Vec<ParseError>),
    /// The text has `#` comments, which the canonical printer cannot carry yet; formatting would
    /// silently delete them.
    #[error("{0} comment(s) would be dropped; comment-preserving formatting is not supported yet")]
    CommentsWouldBeLost(usize),
}

/// Format a whole `.grl` file into its canonical layout: one clause per line, examples last.
///
/// The result is a fixed point: formatting it again returns the same bytes.
///
/// # Errors
///
/// [`FormatError::Syntax`] when the text does not parse; [`FormatError::CommentsWouldBeLost`]
/// when it holds `#` comments.
pub fn format_source(file: FileId, source: &str) -> Result<String, FormatError> {
    let parsed = parse(file, source);
    if !parsed.is_ok() {
        return Err(FormatError::Syntax(parsed.errors));
    }
    if let Ok(lexed) = lex(file, source)
        && !lexed.comments.is_empty()
    {
        return Err(FormatError::CommentsWouldBeLost(lexed.comments.len()));
    }
    Ok(print(&parsed.file))
}
