//! The reason a plan was refused: every untrusted-byte failure names itself.

use thiserror::Error;

/// Why plan bytes or a plan value were rejected; never a panic, always a reason.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum PlanError {
    /// The bytes do not start with the plan magic.
    #[error("not a plan: bad magic")]
    BadMagic,
    /// The format version is not one this engine reads.
    #[error("unsupported plan format version {found} (this engine reads {supported})")]
    UnsupportedVersion {
        /// Version found in the header.
        found: u16,
        /// Version this engine reads.
        supported: u16,
    },
    /// The bytes end before the named item is complete.
    #[error("truncated plan: ended while reading {what}")]
    Truncated {
        /// What was being read.
        what: &'static str,
    },
    /// Bytes remain after the plan.
    #[error("trailing bytes after the plan ({extra} extra)")]
    TrailingBytes {
        /// Number of unread bytes.
        extra: usize,
    },
    /// A count, length or size exceeds its hard limit.
    #[error("{what} is {found}, over the limit of {limit}")]
    TooLarge {
        /// The limited quantity.
        what: &'static str,
        /// The value found.
        found: u64,
        /// The limit.
        limit: u64,
    },
    /// A tag byte names no variant.
    #[error("unknown {what} tag {tag}")]
    BadTag {
        /// The enum being read.
        what: &'static str,
        /// The offending tag.
        tag: u8,
    },
    /// A string is not UTF-8.
    #[error("{what} is not valid UTF-8")]
    BadUtf8 {
        /// The string being read.
        what: &'static str,
    },
    /// An index points past the end of its table.
    #[error("{what} index {index} is out of range (table has {len})")]
    OutOfRange {
        /// The kind of reference.
        what: &'static str,
        /// The index found.
        index: u64,
        /// Table length.
        len: u64,
    },
    /// An operation refers to itself or to a later one, which would allow a cycle.
    #[error("op {op} refers to op {target}, which does not come earlier (cycle)")]
    Cyclic {
        /// The referring op.
        op: u32,
        /// The referenced op.
        target: u32,
    },
    /// An op is referenced more than once (plans are trees over an arena).
    #[error("op {op} is referenced more than once")]
    SharedOp {
        /// The shared op.
        op: u32,
    },
    /// An op is referenced by nothing.
    #[error("op {op} is unreachable")]
    OrphanOp {
        /// The unreachable op.
        op: u32,
    },
    /// An op sits in a position its kind may not occupy.
    #[error("op {op}: {why}")]
    Misplaced {
        /// The op.
        op: u32,
        /// Why it cannot be there.
        why: &'static str,
    },
    /// Nesting is deeper than the limit.
    #[error("plan nesting is deeper than {limit}")]
    TooDeep {
        /// The limit.
        limit: u32,
    },
    /// A variable is used before it is bound, or outside its scope.
    #[error("variable {var} is used where it is not bound")]
    Unbound {
        /// The variable slot.
        var: u16,
    },
    /// A variable slot is bound more than once.
    #[error("variable {var} is bound more than once")]
    Rebound {
        /// The variable slot.
        var: u16,
    },
    /// A declared variable slot is never bound.
    #[error("variable {var} is declared but never bound")]
    UnusedVar {
        /// The variable slot.
        var: u16,
    },
    /// A side relation is read without being declared in `needs`.
    #[error("side relation `{need}` is read but not declared in needs")]
    UndeclaredNeed {
        /// The relation name.
        need: &'static str,
    },
    /// The prefilter omits a node kind the plan finds.
    #[error("prefilter lacks kind `{kind}` that the plan finds")]
    PrefilterMissing {
        /// The kind name.
        kind: String,
    },
    /// The declared cost class disagrees with the ops.
    #[error("cost class disagrees with the plan: {why}")]
    CostMismatch {
        /// What disagrees.
        why: &'static str,
    },
    /// A set that must be sorted and unique is not.
    #[error("{what} must be strictly ascending")]
    NotCanonical {
        /// The set.
        what: &'static str,
    },
    /// A field value is outside its allowed domain.
    #[error("invalid {what}: {why}")]
    Invalid {
        /// The field.
        what: &'static str,
        /// Why it is invalid.
        why: &'static str,
    },
}
