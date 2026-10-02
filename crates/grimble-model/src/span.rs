//! Byte spans and diagnostics produced before findings exist.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use std::fmt;

/// A half-open byte range of one .grmb file.
#[derive(Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Debug, Default)]
pub struct Span {
    /// First byte.
    pub start: usize,
    /// One past the last byte.
    pub end: usize,
}

impl Span {
    /// A span from `start` to `end` (clamped so `end >= start`).
    pub const fn new(start: usize, end: usize) -> Self {
        Self {
            start,
            end: if end < start { start } else { end },
        }
    }

    /// The smallest span covering both.
    #[must_use]
    pub fn to(self, other: Self) -> Self {
        Self::new(self.start.min(other.start), self.end.max(other.end))
    }

    /// The text of `src` this span covers (empty when out of range).
    pub fn slice(self, src: &str) -> &str {
        src.get(self.start..self.end).unwrap_or("")
    }
}

impl fmt::Display for Span {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}..{}", self.start, self.end)
    }
}

/// A problem found while reading one file, before it becomes a finding.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Diagnostic {
    /// The rule id (`MDL000`..`MDL017`, or a directive-scanner id).
    pub rule: &'static str,
    /// Where, in file coordinates.
    pub span: Span,
    /// What is wrong.
    pub message: String,
}

impl Diagnostic {
    /// A diagnostic of `rule` at `span`.
    pub fn new(rule: &'static str, span: Span, message: impl Into<String>) -> Self {
        let message = message.into();
        tracing::debug!(rule, %span, %message, "grmb diagnostic");
        Self {
            rule,
            span,
            message,
        }
    }
}
