//! Snippet renderer: a source line with a caret line under a span.

use std::fmt;

use crate::line_index::LineCol;
use crate::size::TextRange;
use crate::source::SourceText;

/// The first line of a span plus a caret line aligned beneath it.
///
/// `Display` prints the line, a newline, then the caret line (no trailing
/// newline). Tabs in the prefix are kept in the caret line so it aligns.
///
/// ```
/// use gob_text::{SourceText, TextRange, render_snippet};
/// let src = SourceText::new("a = bad\n").unwrap();
/// let s = render_snippet(&src, TextRange::new(4u32.into(), 7u32.into())).unwrap();
/// assert_eq!(s.line_number, 1);
/// assert_eq!(s.to_string(), "a = bad\n    ^^^");
/// ```
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Snippet {
    /// 1-based line number of the span start.
    pub line_number: u32,
    /// Text of that line without its terminator.
    pub line: String,
    /// Spaces/tabs then carets aligned under the span.
    pub caret_line: String,
}

impl fmt::Display for Snippet {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}\n{}", self.line, self.caret_line)
    }
}

/// Render the line holding the start of `range` with carets under it.
///
/// Multi-line spans are clipped to the first line; empty spans get one
/// caret. Returns `None` if `range` is out of bounds or splits a char.
///
/// ```
/// use gob_text::{SourceText, TextRange, render_snippet};
/// let src = SourceText::new("x\n").unwrap();
/// assert!(render_snippet(&src, TextRange::new(5u32.into(), 6u32.into())).is_none());
/// ```
pub fn render_snippet(source: &SourceText, range: TextRange) -> Option<Snippet> {
    let LineCol { line, col } = source.line_col(range.start())?;
    let text = source.as_str();
    let idx = source.line_index();
    let line_start = idx.line_start(line)?;
    let line_end = idx.line_end(text, line)?;
    let line_text = text.get(line_start.to_usize()..line_end.to_usize())?;

    let prefix_len = (col - 1) as usize;
    let prefix = line_text.get(..prefix_len)?;
    let clipped_end = range.end().min(line_end).max(range.start());
    let covered = text.get(range.start().to_usize()..clipped_end.to_usize())?;

    let mut caret_line: String = prefix
        .chars()
        .map(|c| if c == '\t' { '\t' } else { ' ' })
        .collect();
    let carets = covered.chars().count().max(1);
    caret_line.extend(std::iter::repeat_n('^', carets));

    Some(Snippet {
        line_number: line,
        line: line_text.to_owned(),
        caret_line,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn r(a: u32, b: u32) -> TextRange {
        TextRange::new(a.into(), b.into())
    }

    #[test]
    fn multiline_clipped_and_empty_span() {
        let src = SourceText::new("ab\ncd\n").unwrap();
        assert_eq!(render_snippet(&src, r(1, 5)).unwrap().to_string(), "ab\n ^");
        assert_eq!(render_snippet(&src, r(4, 4)).unwrap().to_string(), "cd\n ^");
    }

    #[test]
    fn tabs_and_wide_chars_align_by_char() {
        let src = SourceText::new("\t\u{e9}x\n").unwrap();
        let s = render_snippet(&src, r(3, 4)).unwrap();
        assert_eq!(s.caret_line, "\t ^");
    }

    #[test]
    fn crlf_line_is_trimmed() {
        let src = SourceText::new("ab\r\ncd").unwrap();
        assert_eq!(render_snippet(&src, r(0, 2)).unwrap().line, "ab");
    }

    #[test]
    fn invalid_boundary_is_none() {
        let src = SourceText::new("\u{e9}").unwrap();
        assert!(render_snippet(&src, r(1, 2)).is_none());
    }
}
