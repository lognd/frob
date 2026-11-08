//! Typed errors and notes of the scene solver.

// frob:ticket 01M5XCWYB9M2YSJ5EGABMREX1B

use crate::output::{Axis, OutputError};
use crate::style::{StyleError, StyleFinding};
use crate::text::TextError;

/// Why a scene could not be solved.
#[derive(Debug, thiserror::Error)]
pub enum SolveError {
    /// SCENE002 holds (duplicate or missing `data-id`): the context is not solved.
    #[error("SCENE002: context not solved: {}", .0.join("; "))]
    Refused(Vec<String>),
    /// One or more elements' styles could not be mapped.
    #[error("{} style error(s); first: {}", .0.len(), .0[0])]
    Style(Vec<StyleError>),
    /// Text could not be measured (a font outside the bundle).
    #[error(transparent)]
    Text(#[from] TextError),
    /// taffy refused the tree or the layout (an internal inconsistency).
    #[error("layout engine error: {0}")]
    Engine(String),
    /// The result could not be normalized or serialized.
    #[error(transparent)]
    Output(#[from] OutputError),
}

/// A non-fatal observation made while solving.
#[derive(Debug, Clone, PartialEq)]
pub enum SolveNote {
    /// An unknown tag was laid out as an empty block.
    UnknownTag {
        /// The element's `data-id`.
        id: String,
        /// The tag as written.
        tag: String,
    },
    /// A glyph came from the fallback font (`missing_glyph`).
    MissingGlyph {
        /// The text node's id.
        id: String,
    },
    /// A root is larger than the viewport.
    PageOverflow {
        /// The root's id.
        id: String,
        /// The overflowing axis.
        axis: Axis,
        /// By how many pixels.
        amount: f32,
    },
    /// A style-mapping finding.
    Style(StyleFinding),
}
