//! The answer lattice and Kleene three-valued truth (universal-model.md 4.1).

use std::fmt;
use std::ops::{BitAnd, BitOr, Not};

/// The result of a structural query: how much the adapter can claim.
///
/// ```
/// use gob_ir::Answer;
/// let a: Answer<u32> = Answer::Exact(3);
/// assert_eq!(a.lo(), Some(&3));
/// assert_eq!(a.hi(), Some(&3));
/// ```
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Answer<T> {
    /// The value is known and complete.
    Exact(T),
    /// The true value lies between `lo` (must) and `hi` (may).
    Bounds {
        /// The part certainly in the answer.
        lo: T,
        /// The part possibly in the answer.
        hi: T,
    },
    /// No claim can be made.
    Unknown,
    /// The language has no such feature; a query answer, never a finding.
    NotApplicable,
}

impl<T> Answer<T> {
    /// The certain part: the exact value or the lower bound.
    pub fn lo(&self) -> Option<&T> {
        match self {
            Self::Exact(v) | Self::Bounds { lo: v, .. } => Some(v),
            Self::Unknown | Self::NotApplicable => None,
        }
    }

    /// The possible part: the exact value or the upper bound.
    pub fn hi(&self) -> Option<&T> {
        match self {
            Self::Exact(v) | Self::Bounds { hi: v, .. } => Some(v),
            Self::Unknown | Self::NotApplicable => None,
        }
    }

    /// True for [`Answer::Exact`].
    pub fn is_exact(&self) -> bool {
        matches!(self, Self::Exact(_))
    }

    /// The exact value, if any.
    pub fn exact(self) -> Option<T> {
        match self {
            Self::Exact(v) => Some(v),
            _ => None,
        }
    }

    /// Apply `f` to every carried value, preserving the lattice shape.
    pub fn map<U>(self, mut f: impl FnMut(T) -> U) -> Answer<U> {
        match self {
            Self::Exact(v) => Answer::Exact(f(v)),
            Self::Bounds { lo, hi } => Answer::Bounds {
                lo: f(lo),
                hi: f(hi),
            },
            Self::Unknown => Answer::Unknown,
            Self::NotApplicable => Answer::NotApplicable,
        }
    }
}

/// Kleene's strong three-valued truth.
///
/// ```
/// use gob_ir::Truth;
/// assert_eq!(Truth::No & Truth::Unknown, Truth::No);
/// assert_eq!(Truth::Yes | Truth::Unknown, Truth::Yes);
/// assert_eq!(!Truth::Unknown, Truth::Unknown);
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Truth {
    /// Definitely false (ordered lowest so `min` is conjunction).
    No,
    /// Not decided by the syntax.
    Unknown,
    /// Definitely true.
    Yes,
}

impl Truth {
    /// Lift a classical boolean.
    pub const fn from_bool(b: bool) -> Self {
        if b { Self::Yes } else { Self::No }
    }

    /// Kleene conjunction.
    #[must_use]
    pub fn and(self, other: Self) -> Self {
        self.min(other)
    }

    /// Kleene disjunction.
    #[must_use]
    pub fn or(self, other: Self) -> Self {
        self.max(other)
    }

    /// Conjunction over an iterator; `Yes` when empty.
    pub fn all(items: impl IntoIterator<Item = Self>) -> Self {
        items.into_iter().fold(Self::Yes, Self::and)
    }

    /// Disjunction over an iterator; `No` when empty.
    pub fn any(items: impl IntoIterator<Item = Self>) -> Self {
        items.into_iter().fold(Self::No, Self::or)
    }

    /// True only for a definite `Yes`.
    pub const fn is_yes(self) -> bool {
        matches!(self, Self::Yes)
    }

    /// True only for `Unknown`.
    pub const fn is_unknown(self) -> bool {
        matches!(self, Self::Unknown)
    }
}

impl From<bool> for Truth {
    fn from(b: bool) -> Self {
        Self::from_bool(b)
    }
}

impl Not for Truth {
    type Output = Self;
    fn not(self) -> Self {
        match self {
            Self::Yes => Self::No,
            Self::No => Self::Yes,
            Self::Unknown => Self::Unknown,
        }
    }
}

impl BitAnd for Truth {
    type Output = Self;
    fn bitand(self, rhs: Self) -> Self {
        self.and(rhs)
    }
}

impl BitOr for Truth {
    type Output = Self;
    fn bitor(self, rhs: Self) -> Self {
        self.or(rhs)
    }
}

impl fmt::Display for Truth {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::Yes => "yes",
            Self::No => "no",
            Self::Unknown => "unknown",
        })
    }
}
