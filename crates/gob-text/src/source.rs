//! `SourceText`: shared text plus a lazily built `LineIndex`.

use std::sync::{Arc, OnceLock};

use crate::line_index::{LineCol, LineIndex};
use crate::size::{TextRange, TextSize, TextTooLarge};

#[derive(Debug)]
struct Inner {
    text: Arc<str>,
    index: OnceLock<LineIndex>,
}

/// Immutable source text, cheap to clone, with a lazily built line index.
///
/// ```
/// use gob_text::{SourceText, TextSize, LineCol};
/// let src = SourceText::new("one\ntwo").unwrap();
/// assert_eq!(src.line_col(TextSize::new(5)), Some(LineCol { line: 2, col: 2 }));
/// assert_eq!(src.line_text(2), Some("two"));
/// ```
#[derive(Debug, Clone)]
pub struct SourceText {
    inner: Arc<Inner>,
}

impl SourceText {
    /// Wrap `text`; fails if it is larger than `u32::MAX` bytes.
    ///
    /// # Errors
    ///
    /// Returns [`TextTooLarge`] when the text length does not fit in `u32`.
    pub fn new(text: impl Into<Arc<str>>) -> Result<Self, TextTooLarge> {
        let text = text.into();
        TextSize::try_from(text.len())?;
        Ok(Self {
            inner: Arc::new(Inner {
                text,
                index: OnceLock::new(),
            }),
        })
    }

    /// The full text.
    pub fn as_str(&self) -> &str {
        &self.inner.text
    }

    /// Length in bytes.
    pub fn len(&self) -> TextSize {
        TextSize::try_from(self.inner.text.len()).unwrap_or_default()
    }

    /// Whether the text is empty.
    pub fn is_empty(&self) -> bool {
        self.inner.text.is_empty()
    }

    /// The line index, built on first use.
    ///
    /// # Panics
    ///
    /// Never in practice: the length was validated in [`SourceText::new`].
    pub fn line_index(&self) -> &LineIndex {
        self.inner.index.get_or_init(|| {
            // Length was validated in `new`, so indexing cannot fail.
            LineIndex::new(&self.inner.text).expect("length validated in SourceText::new")
        })
    }

    /// 1-based line and byte column of `offset`.
    pub fn line_col(&self, offset: TextSize) -> Option<LineCol> {
        self.line_index().line_col(offset)
    }

    /// 1-based UTF-16 column of `offset`.
    pub fn utf16_col(&self, offset: TextSize) -> Option<u32> {
        self.line_index().utf16_col(&self.inner.text, offset)
    }

    /// The slice of text covered by `range`, if in bounds and on char boundaries.
    pub fn slice(&self, range: TextRange) -> Option<&str> {
        self.inner.text.get(range.to_usize_range())
    }

    /// The text of 1-based `line` without its terminator.
    pub fn line_text(&self, line: u32) -> Option<&str> {
        let idx = self.line_index();
        let start = idx.line_start(line)?;
        let end = idx.line_end(&self.inner.text, line)?;
        self.inner.text.get(start.to_usize()..end.to_usize())
    }
}

impl PartialEq for SourceText {
    fn eq(&self, other: &Self) -> bool {
        self.inner.text == other.inner.text
    }
}

impl Eq for SourceText {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lazy_index_and_slices() {
        let src = SourceText::new("h\u{e9}llo\nw").unwrap();
        assert_eq!(src.line_text(1), Some("h\u{e9}llo"));
        assert_eq!(src.line_text(2), Some("w"));
        assert_eq!(src.line_text(3), None);
        assert_eq!(
            src.slice(TextRange::new(0.into(), 3.into())),
            Some("h\u{e9}")
        );
        assert_eq!(src.slice(TextRange::new(0.into(), 2.into())), None);
        assert_eq!(src.clone(), src);
    }
}
