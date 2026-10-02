//! The six-component specificity vector of grmb-spec 6.5.

// frob:ticket 01M3Z713RETBN30XBC6CK11FBF

use std::fmt;

/// How specific a matching selector is; compared lexicographically, larger wins.
///
/// The components are, in order: level (3 symbol, 2 file, 1 directory pattern), literal
/// PATH segments, minus `**` segments, minus wildcard segments, literal QUALNAME
/// segments, and the number of restricting predicates.
///
/// ```
/// use gob_walk::Specificity;
/// let dir = Specificity::new([1, 1, -1, 0, 0, 0]);
/// let nested = Specificity::new([1, 2, 0, -1, 0, 0]);
/// assert!(nested > dir);
/// ```
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Debug, Default)]
pub struct Specificity {
    level: i32,
    literal_segments: i32,
    neg_double_star: i32,
    neg_wild_segments: i32,
    literal_qual: i32,
    predicates: i32,
}

impl Specificity {
    /// The bottom vector: no glob, no predicate (a bare negation).
    pub const BOTTOM: Self = Self::new([0; 6]);

    /// A vector from its six components in the order of grmb-spec 6.5.
    pub const fn new(c: [i32; 6]) -> Self {
        Self {
            level: c[0],
            literal_segments: c[1],
            neg_double_star: c[2],
            neg_wild_segments: c[3],
            literal_qual: c[4],
            predicates: c[5],
        }
    }

    /// The vector of one restricting predicate (`lang`, `kind`, `attr`).
    pub const fn predicate() -> Self {
        Self::new([0, 0, 0, 0, 0, 1])
    }

    /// The six components in order.
    pub const fn components(&self) -> [i32; 6] {
        [
            self.level,
            self.literal_segments,
            self.neg_double_star,
            self.neg_wild_segments,
            self.literal_qual,
            self.predicates,
        ]
    }

    /// The vector of `a & b`: the larger of the glob components, predicate counts added.
    #[must_use]
    pub fn and(self, other: Self) -> Self {
        let mut top = if self.without_predicates() >= other.without_predicates() {
            self
        } else {
            other
        };
        top.predicates = self.predicates + other.predicates;
        top
    }

    fn without_predicates(self) -> Self {
        Self {
            predicates: 0,
            ..self
        }
    }
}

impl fmt::Display for Specificity {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let c = self.components();
        write!(
            f,
            "({}, {}, {}, {}, {}, {})",
            c[0], c[1], c[2], c[3], c[4], c[5]
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn review_m12_example_orders_the_nested_glob_first() {
        let dir = Specificity::new([1, 1, -1, 0, 0, 0]);
        let nested = Specificity::new([1, 2, 0, -1, 0, 0]);
        assert!(nested > dir);
    }

    #[test]
    fn level_dominates_everything_below_it() {
        let symbol = Specificity::new([3, 0, -9, -9, 0, 0]);
        let file = Specificity::new([2, 9, 0, 0, 9, 9]);
        assert!(symbol > file);
    }

    #[test]
    fn fewer_double_stars_beat_more_at_equal_literals() {
        let a = Specificity::new([1, 2, -1, 0, 0, 0]);
        let b = Specificity::new([1, 2, -2, 0, 0, 0]);
        assert!(a > b);
    }

    #[test]
    fn predicates_break_the_last_tie_only() {
        let plain = Specificity::new([1, 1, -1, 0, 0, 0]);
        let narrowed = Specificity::new([1, 1, -1, 0, 0, 2]);
        assert!(narrowed > plain);
        assert!(plain > Specificity::new([1, 0, -1, 0, 0, 5]));
    }

    #[test]
    fn and_takes_the_larger_glob_and_adds_predicates() {
        let glob = Specificity::new([1, 2, -1, 0, 0, 0]);
        let both = glob
            .and(Specificity::predicate())
            .and(Specificity::predicate());
        assert_eq!(both.components(), [1, 2, -1, 0, 0, 2]);
        assert_eq!(Specificity::BOTTOM.and(glob), glob);
    }

    #[test]
    fn bottom_is_below_any_glob() {
        assert!(Specificity::BOTTOM < Specificity::new([1, 0, -5, -5, 0, 0]));
        assert_eq!(
            Specificity::new([1, 1, -1, 0, 0, 0]).to_string(),
            "(1, 1, -1, 0, 0, 0)"
        );
    }
}
