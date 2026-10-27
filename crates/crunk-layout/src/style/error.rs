//! The typed errors and non-fatal findings of the style mapping.

// frob:ticket 01M5XCWXYNXW0RW8VRDQPY31M6

use std::fmt;

/// Why a scene could not be mapped to taffy styles; every variant names the element and line.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum StyleError {
    /// A `var(--x)` names a token the token map does not define and gives no fallback.
    #[error("element `{element}` (line {line}): `{property}` uses undefined token `{token}`")]
    UndefinedToken {
        /// The element's `data-id`.
        element: String,
        /// 1-based line of the element's start tag.
        line: u32,
        /// The property whose value used the token.
        property: String,
        /// The token name, with its leading `--`.
        token: String,
    },
    /// A token's value refers back to itself through other tokens (or nests too deeply).
    #[error("element `{element}` (line {line}): `{property}` hits a token cycle at `{token}`")]
    TokenCycle {
        /// The element's `data-id`.
        element: String,
        /// 1-based line of the element's start tag.
        line: u32,
        /// The property whose value used the token.
        property: String,
        /// The token where the cycle was detected.
        token: String,
    },
    /// A declaration's value is malformed or outside what the solver implements.
    #[error("element `{element}` (line {line}): bad value `{value}` for `{property}`: {reason}")]
    BadValue {
        /// The element's `data-id`.
        element: String,
        /// 1-based line of the element's start tag.
        line: u32,
        /// The property.
        property: String,
        /// The value as written (after token substitution when that happened).
        value: String,
        /// Why it is rejected.
        reason: String,
    },
    /// Two elements share a `data-id`, so the tree cannot be keyed by it.
    #[error("element `{element}` (line {line}): data-id already used on line {first_line}")]
    DuplicateDataId {
        /// The repeated `data-id`.
        element: String,
        /// 1-based line of the second use.
        line: u32,
        /// 1-based line of the first use.
        first_line: u32,
    },
    /// taffy refused to build the tree (an internal inconsistency, not bad input).
    #[error("layout engine error: {0}")]
    Engine(String),
}

/// What kind of non-fatal problem a [`StyleFinding`] reports.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FindingKind {
    /// A padding, gap, border width, size or flex factor was negative; it was clamped (or ignored).
    NegativeValue,
    /// A percentage size under a parent with no definite size on that axis was treated as auto.
    PercentUnderIndefiniteParent,
    /// `aspect-ratio` was ignored because both width and height are set.
    AspectRatioIgnored,
    /// A minimum exceeded its maximum; the maximum was raised to the minimum (the CSS rule).
    MinExceedsMax,
    /// A layout property the solver does not map yet was left out.
    UnmappedProperty,
    /// Rules of a `<style>` body were not applied (only inline `style` attributes are mapped).
    StylesheetNotApplied,
    /// An element has no usable `data-id` and was left out of the tree (SCENE002 reports it).
    MissingDataId,
}

/// One non-fatal problem found while mapping an element.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StyleFinding {
    /// What kind of problem.
    pub kind: FindingKind,
    /// The element's `data-id` (empty when the finding is about the whole scene).
    pub element: String,
    /// 1-based line.
    pub line: u32,
    /// The property involved, when there is one.
    pub property: String,
    /// A human sentence.
    pub message: String,
}

impl fmt::Display for StyleFinding {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "element `{}` (line {}): {:?}: {}",
            self.element, self.line, self.kind, self.message
        )
    }
}
