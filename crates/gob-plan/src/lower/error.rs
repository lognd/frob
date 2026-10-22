//! Why a rule could not be lowered to a plan.

// frob:ticket 01M3ZX7EKNE5Q0NB0DKCH77AZX
use gob_text::Span;

use crate::plan::PlanError;

/// A lowering failure; every variant names the source range to point at.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum LowerError {
    /// The rule uses a construct the plan IR or this lowering does not cover yet.
    #[error("cannot lower {what} yet")]
    Unsupported {
        /// The construct, in the author's words.
        what: &'static str,
        /// Where it is written.
        span: Span,
    },
    /// A variable is used but bound by no `find` (the checker's GRL003, reached without it).
    #[error("variable `{name}` is not bound")]
    UnknownVar {
        /// The variable.
        name: String,
        /// Where it is used.
        span: Span,
    },
    /// A variable is bound twice (the checker's GRL004).
    #[error("variable `{name}` is bound twice")]
    Duplicate {
        /// The variable.
        name: String,
        /// The second binding.
        span: Span,
    },
    /// A `needs` word names no capability, or a `reads` word no side relation.
    #[error("unknown capability or side relation `{name}`")]
    UnknownNeed {
        /// The word.
        name: String,
        /// Where it is written.
        span: Span,
    },
    /// The lowering met a state it should never produce (a bug, reported instead of a panic).
    #[error("internal lowering error: {what}")]
    Internal {
        /// What went wrong.
        what: &'static str,
    },
    /// The lowered plan failed validation.
    #[error("the lowered plan is invalid: {0}")]
    Plan(#[from] PlanError),
}
