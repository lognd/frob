//! A three-valued answer together with the doubts that decide it.
//!
//! The connectives are Kleene's (`gob_ir::Truth`); a [`Verdict`] additionally carries the
//! [`Doubt`]s that make an `Unknown` unknown, and only those: a `No` that absorbs an `Unknown`
//! under `and` carries no doubt, because the doubt did not matter. Polarity (`outcome`) turns
//! the surviving doubts into the typed reason of an Unresolved finding.

use std::ops::Not;

use gob_ir::{NodeId, Truth};

/// One reason a condition could not be decided.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum Doubt {
    /// A quantifier ranged over a model with unread regions (opaque or hole nodes), which may
    /// hide members of any kind (review 2.2 item 7).
    Hidden,
    /// A field or operand cannot be read statically (a dynamic value, a spread, no source text).
    Dynamic {
        /// The node whose field was read, when there was one.
        node: Option<NodeId>,
        /// The field, or a description of the operand.
        field: String,
    },
    /// A node is a member of its kind only at status May (an attribute spread).
    Member {
        /// The node.
        node: NodeId,
    },
}

impl Not for Verdict {
    type Output = Self;

    /// Kleene negation; the doubts of an `Unknown` stay.
    fn not(self) -> Self {
        Self {
            truth: !self.truth,
            doubts: self.doubts,
        }
    }
}

/// A Kleene truth with the doubts behind an `Unknown`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Verdict {
    /// The truth.
    pub truth: Truth,
    /// Why it is `Unknown`; empty unless `truth` is `Unknown`.
    pub doubts: Vec<Doubt>,
}

impl Verdict {
    /// A definite truth with no doubts.
    pub fn certain(truth: bool) -> Self {
        Self {
            truth: Truth::from_bool(truth),
            doubts: Vec::new(),
        }
    }

    /// `Yes`.
    pub fn yes() -> Self {
        Self::certain(true)
    }

    /// `No`.
    pub fn no() -> Self {
        Self::certain(false)
    }

    /// `Unknown` because of `doubt`.
    pub fn unknown(doubt: Doubt) -> Self {
        Self {
            truth: Truth::Unknown,
            doubts: vec![doubt],
        }
    }

    /// A truth from a datum comparison: an `Unknown` carries `doubt`.
    pub fn of(truth: Truth, doubt: impl FnOnce() -> Doubt) -> Self {
        match truth {
            Truth::Unknown => Self::unknown(doubt()),
            t => Self {
                truth: t,
                doubts: Vec::new(),
            },
        }
    }

    /// Kleene conjunction: a `No` decides alone; otherwise doubts accumulate.
    #[must_use]
    pub fn and(self, other: Self) -> Self {
        Self::join(self, other, Truth::No)
    }

    /// Kleene disjunction: a `Yes` decides alone; otherwise doubts accumulate.
    #[must_use]
    pub fn or(self, other: Self) -> Self {
        Self::join(self, other, Truth::Yes)
    }

    /// Combine under the connective whose absorbing element is `absorb`.
    fn join(a: Self, b: Self, absorb: Truth) -> Self {
        if a.truth == absorb {
            return a;
        }
        if b.truth == absorb {
            return b;
        }
        match (a.truth, b.truth) {
            (Truth::Unknown, _) | (_, Truth::Unknown) => {
                let mut doubts = a.doubts;
                for d in b.doubts {
                    if !doubts.contains(&d) {
                        doubts.push(d);
                    }
                }
                Self {
                    truth: Truth::Unknown,
                    doubts,
                }
            }
            // Both are the identity of the connective.
            _ => a,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const ALL: [Truth; 3] = [Truth::No, Truth::Unknown, Truth::Yes];

    fn v(t: Truth) -> Verdict {
        match t {
            Truth::Unknown => Verdict::unknown(Doubt::Hidden),
            t => Verdict::certain(t == Truth::Yes),
        }
    }

    // frob:tests crates/gob-plan/src/exec/core/verdict.rs::Verdict.and
    // frob:tests crates/gob-plan/src/exec/core/verdict.rs::Verdict.or
    #[test]
    fn connectives_are_kleene_and_doubts_only_survive_when_they_matter() {
        for a in ALL {
            for b in ALL {
                assert_eq!(v(a).and(v(b)).truth, a & b);
                assert_eq!(v(a).or(v(b)).truth, a | b);
            }
            assert_eq!((!v(a)).truth, !a);
        }
        assert!(v(Truth::No).and(v(Truth::Unknown)).doubts.is_empty());
        assert!(v(Truth::Yes).or(v(Truth::Unknown)).doubts.is_empty());
        assert_eq!(
            v(Truth::Yes).and(v(Truth::Unknown)).doubts,
            vec![Doubt::Hidden]
        );
        assert_eq!(
            v(Truth::No).or(v(Truth::Unknown)).doubts,
            vec![Doubt::Hidden]
        );
    }
}
