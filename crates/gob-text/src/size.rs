//! `TextSize` and `TextRange`: `u32` byte offsets and half-open ranges.

use std::fmt;

/// Error returned when a length or offset does not fit in `u32`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TextTooLarge;

impl fmt::Display for TextTooLarge {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("text offset exceeds u32::MAX bytes")
    }
}

impl std::error::Error for TextTooLarge {}

/// A byte offset or length into a text, stored as `u32`.
///
/// ```
/// use gob_text::TextSize;
/// assert_eq!(u32::from(TextSize::new(7)), 7);
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Default)]
pub struct TextSize(u32);

impl TextSize {
    /// Wrap a raw byte count.
    pub const fn new(raw: u32) -> Self {
        Self(raw)
    }

    /// The raw byte count as `usize`, for indexing.
    pub const fn to_usize(self) -> usize {
        self.0 as usize
    }
}

impl From<u32> for TextSize {
    fn from(raw: u32) -> Self {
        Self(raw)
    }
}

impl From<TextSize> for u32 {
    fn from(size: TextSize) -> Self {
        size.0
    }
}

impl TryFrom<usize> for TextSize {
    type Error = TextTooLarge;

    fn try_from(value: usize) -> Result<Self, Self::Error> {
        u32::try_from(value).map(Self).map_err(|_| TextTooLarge)
    }
}

impl fmt::Display for TextSize {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.0.fmt(f)
    }
}

/// A half-open byte range `[start, end)` with `start <= end`.
///
/// ```
/// use gob_text::{TextRange, TextSize};
/// let r = TextRange::new(2u32.into(), 5u32.into());
/// assert_eq!(r.len(), TextSize::new(3));
/// assert!(r.contains(TextSize::new(2)) && !r.contains(TextSize::new(5)));
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub struct TextRange {
    start: TextSize,
    end: TextSize,
}

impl TextRange {
    /// Build a range from endpoints.
    ///
    /// # Panics
    ///
    /// Panics if `start > end` (a programmer bug).
    pub fn new(start: TextSize, end: TextSize) -> Self {
        assert!(start <= end, "TextRange start {start} > end {end}");
        Self { start, end }
    }

    /// Build a range from a start and a length (saturating at `u32::MAX`).
    pub fn at(start: TextSize, len: TextSize) -> Self {
        Self {
            start,
            end: TextSize(start.0.saturating_add(len.0)),
        }
    }

    /// An empty range at `offset`.
    pub const fn empty(offset: TextSize) -> Self {
        Self {
            start: offset,
            end: offset,
        }
    }

    /// Inclusive start offset.
    pub const fn start(self) -> TextSize {
        self.start
    }

    /// Exclusive end offset.
    pub const fn end(self) -> TextSize {
        self.end
    }

    /// Length in bytes.
    pub const fn len(self) -> TextSize {
        TextSize(self.end.0 - self.start.0)
    }

    /// Whether the range covers no bytes.
    pub const fn is_empty(self) -> bool {
        self.start.0 == self.end.0
    }

    /// Whether `offset` lies in `[start, end)`.
    pub fn contains(self, offset: TextSize) -> bool {
        self.start <= offset && offset < self.end
    }

    /// Whether `other` lies entirely within this range.
    pub fn contains_range(self, other: TextRange) -> bool {
        self.start <= other.start && other.end <= self.end
    }

    /// The smallest range covering both ranges.
    #[must_use]
    pub fn cover(self, other: TextRange) -> TextRange {
        TextRange {
            start: self.start.min(other.start),
            end: self.end.max(other.end),
        }
    }

    /// The overlap of both ranges, if they share at least a point.
    pub fn intersect(self, other: TextRange) -> Option<TextRange> {
        let start = self.start.max(other.start);
        let end = self.end.min(other.end);
        (start <= end).then_some(TextRange { start, end })
    }

    /// The range as a `usize` slice range.
    pub fn to_usize_range(self) -> std::ops::Range<usize> {
        self.start.to_usize()..self.end.to_usize()
    }
}

impl fmt::Display for TextRange {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}..{}", self.start, self.end)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cover_and_intersect() {
        let a = TextRange::new(1.into(), 4.into());
        let b = TextRange::new(3.into(), 9.into());
        assert_eq!(a.cover(b), TextRange::new(1.into(), 9.into()));
        assert_eq!(a.intersect(b), Some(TextRange::new(3.into(), 4.into())));
        assert_eq!(a.intersect(TextRange::new(6.into(), 7.into())), None);
    }

    #[test]
    fn try_from_usize_rejects_overflow() {
        assert!(TextSize::try_from(usize::MAX).is_err());
        assert_eq!(TextSize::try_from(5usize), Ok(TextSize::new(5)));
    }

    #[test]
    #[should_panic(expected = "start")]
    fn inverted_range_panics() {
        let _ = TextRange::new(5.into(), 1.into());
    }
}
