//! `LineIndex`: byte offset to line/column and back.

use crate::size::{TextSize, TextTooLarge};

/// A 1-based line and 1-based UTF-8 byte column.
///
/// ```
/// use gob_text::LineCol;
/// let lc = LineCol { line: 2, col: 3 };
/// assert_eq!(lc.to_string(), "2:3");
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct LineCol {
    /// 1-based line number.
    pub line: u32,
    /// 1-based column, counted in UTF-8 bytes from the line start.
    pub col: u32,
}

impl std::fmt::Display for LineCol {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}:{}", self.line, self.col)
    }
}

/// Start offsets of every line of a text (lines end at `\n`; `\r\n` works).
///
/// ```
/// use gob_text::{LineIndex, LineCol, TextSize};
/// let idx = LineIndex::new("ab\ncd").unwrap();
/// assert_eq!(idx.line_col(TextSize::new(4)), Some(LineCol { line: 2, col: 2 }));
/// assert_eq!(idx.offset(LineCol { line: 2, col: 2 }), Some(TextSize::new(4)));
/// ```
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LineIndex {
    line_starts: Vec<TextSize>,
    len: TextSize,
}

impl LineIndex {
    /// Index `text`; fails if it is larger than `u32::MAX` bytes.
    ///
    /// # Errors
    ///
    /// Returns [`TextTooLarge`] when `text.len()` does not fit in `u32`.
    pub fn new(text: &str) -> Result<Self, TextTooLarge> {
        let len = TextSize::try_from(text.len())?;
        let mut line_starts = vec![TextSize::new(0)];
        for (i, b) in text.bytes().enumerate() {
            if b == b'\n' {
                // i + 1 <= len, which fits in u32 (checked above).
                line_starts.push(TextSize::try_from(i + 1)?);
            }
        }
        Ok(Self { line_starts, len })
    }

    /// Number of lines (a trailing newline starts a final empty line).
    pub fn line_count(&self) -> usize {
        self.line_starts.len()
    }

    /// Total text length in bytes.
    pub fn text_len(&self) -> TextSize {
        self.len
    }

    /// Start offset of 1-based `line`, or `None` if out of range.
    pub fn line_start(&self, line: u32) -> Option<TextSize> {
        let i = usize::try_from(line.checked_sub(1)?).ok()?;
        self.line_starts.get(i).copied()
    }

    /// End offset of 1-based `line`, excluding the line terminator.
    pub fn line_end(&self, text: &str, line: u32) -> Option<TextSize> {
        let start = self.line_start(line)?;
        let next = self.line_start(line + 1).unwrap_or(self.len);
        let mut end = next.to_usize();
        let bytes = text.as_bytes();
        if end > start.to_usize() && bytes[end - 1] == b'\n' {
            end -= 1;
            if end > start.to_usize() && bytes[end - 1] == b'\r' {
                end -= 1;
            }
        }
        TextSize::try_from(end).ok()
    }

    /// 1-based line and byte column of `offset`; `None` past the end.
    pub fn line_col(&self, offset: TextSize) -> Option<LineCol> {
        if offset > self.len {
            return None;
        }
        let line_idx = self.line_starts.partition_point(|s| *s <= offset) - 1;
        let start = self.line_starts[line_idx];
        Some(LineCol {
            line: u32::try_from(line_idx).ok()? + 1,
            col: u32::from(offset) - u32::from(start) + 1,
        })
    }

    /// Inverse of [`LineIndex::line_col`]; `None` if out of range.
    pub fn offset(&self, lc: LineCol) -> Option<TextSize> {
        let start = self.line_start(lc.line)?;
        let off = u32::from(start).checked_add(lc.col.checked_sub(1)?)?;
        // A column may point at most at the end of its line (the newline
        // itself or EOF), never into the next line.
        let limit = self
            .line_start(lc.line + 1)
            .map_or(u32::from(self.len), |n| u32::from(n) - 1);
        (off <= limit).then_some(TextSize::new(off))
    }

    /// 1-based column of `offset` counted in UTF-16 code units (for LSP).
    ///
    /// `text` must be the text this index was built from. Returns `None`
    /// if `offset` is out of range or not on a char boundary.
    pub fn utf16_col(&self, text: &str, offset: TextSize) -> Option<u32> {
        let lc = self.line_col(offset)?;
        let start = self.line_start(lc.line)?.to_usize();
        let line_prefix = text.get(start..offset.to_usize())?;
        let units: usize = line_prefix.chars().map(char::len_utf16).sum();
        Some(u32::try_from(units).ok()? + 1)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    #[test]
    fn crlf_and_trailing_newline() {
        let text = "a\r\nb\n";
        let idx = LineIndex::new(text).unwrap();
        assert_eq!(idx.line_count(), 3);
        assert_eq!(idx.line_end(text, 1), Some(TextSize::new(1)));
        assert_eq!(idx.line_end(text, 2), Some(TextSize::new(4)));
        assert_eq!(idx.line_end(text, 3), Some(TextSize::new(5)));
        assert_eq!(idx.line_start(0), None);
    }

    #[test]
    fn out_of_range() {
        let idx = LineIndex::new("ab").unwrap();
        assert_eq!(idx.line_col(TextSize::new(3)), None);
        assert_eq!(idx.offset(LineCol { line: 1, col: 4 }), None);
        assert_eq!(idx.offset(LineCol { line: 1, col: 0 }), None);
    }

    #[test]
    fn utf16_columns() {
        let text = "a\u{1F600}b";
        let idx = LineIndex::new(text).unwrap();
        // 'b' is at byte 5, after 1 + 2 UTF-16 units.
        assert_eq!(idx.utf16_col(text, TextSize::new(5)), Some(4));
        // Offset inside the emoji is not a char boundary.
        assert_eq!(idx.utf16_col(text, TextSize::new(2)), None);
    }

    proptest! {
        #[test]
        fn offset_roundtrip(text in "\\PC*\n?\\PC*\r?\n?\\PC*", pick in any::<prop::sample::Index>()) {
            let idx = LineIndex::new(&text).unwrap();
            let offset = TextSize::try_from(pick.index(text.len() + 1)).unwrap();
            let lc = idx.line_col(offset).unwrap();
            prop_assert!(lc.line >= 1 && lc.col >= 1);
            prop_assert_eq!(idx.offset(lc), Some(offset));
        }

        #[test]
        fn line_starts_are_consistent(text in "[a-z\u{e9}\u{1F600}\n]*") {
            let idx = LineIndex::new(&text).unwrap();
            prop_assert_eq!(idx.line_count(), text.matches('\n').count() + 1);
            for line in 1..=u32::try_from(idx.line_count()).unwrap() {
                let s = idx.line_start(line).unwrap();
                prop_assert_eq!(idx.line_col(s), Some(LineCol { line, col: 1 }));
            }
        }
    }
}
