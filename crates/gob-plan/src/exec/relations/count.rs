//! Counts as intervals, interval comparison, and knob overrides (grl-spec.md 7.0.2, 7.1).
//!
//! `count(x: SRC where c)` denotes `[l, h]`: `l` counts the members for which the condition is
//! certainly true, `h` those for which it is not certainly false, and `h` is unbounded when the
//! domain is open. Only interval comparison is offered on counts: a non-monotone predicate
//! ("count is even") at the endpoints of an interval is unsound (Ross and Sagiv 1992).

use std::collections::BTreeMap;

use gob_ir::Truth;

use crate::plan::CmpOp;

/// An interval `[lo, hi]` of counts; `hi` is `None` for unbounded (an open domain).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Count {
    /// The members certainly counted.
    pub lo: u64,
    /// The members possibly counted; `None` is unbounded.
    pub hi: Option<u64>,
}

/// `x <= y` over naturals with `None` as infinity.
fn le(x: Option<u64>, y: Option<u64>) -> bool {
    match (x, y) {
        (_, None) => true,
        (None, Some(_)) => false,
        (Some(a), Some(b)) => a <= b,
    }
}

/// `x < y` over naturals with `None` as infinity.
fn lt(x: Option<u64>, y: Option<u64>) -> bool {
    !le(y, x)
}

impl Count {
    /// The known number `n`: `[n, n]`.
    pub fn exactly(n: u64) -> Self {
        Self { lo: n, hi: Some(n) }
    }

    /// Kleene comparison of two count intervals.
    ///
    /// `<` is Yes iff `self.hi < other.lo` and No iff `self.lo >= other.hi`; `<=` is Yes iff
    /// `self.hi <= other.lo` and No iff `self.lo > other.hi`; `==` is Yes only for four equal
    /// finite endpoints and No iff the intervals are disjoint; `>`, `>=` and `!=` follow by
    /// symmetry and negation. Everything else is Unknown.
    pub fn compare(&self, op: CmpOp, other: &Self) -> Truth {
        match op {
            CmpOp::Lt => self.less(other, true),
            CmpOp::Le => self.less(other, false),
            CmpOp::Gt => other.less(self, true),
            CmpOp::Ge => other.less(self, false),
            CmpOp::Eq => self.equal(other),
            CmpOp::Ne => !self.equal(other),
        }
    }

    /// `self < other` (strict) or `self <= other`.
    fn less(&self, other: &Self, strict: bool) -> Truth {
        let (a, b) = (Some(self.lo), self.hi);
        let (c, d) = (Some(other.lo), other.hi);
        let (yes, no) = if strict {
            (lt(b, c), le(d, a))
        } else {
            (le(b, c), lt(d, a))
        };
        if yes {
            Truth::Yes
        } else if no {
            Truth::No
        } else {
            Truth::Unknown
        }
    }

    fn equal(&self, other: &Self) -> Truth {
        let (a, b) = (Some(self.lo), self.hi);
        let (c, d) = (Some(other.lo), other.hi);
        if a == b && c == d && a == c {
            Truth::Yes
        } else if lt(b, c) || lt(d, a) {
            Truth::No
        } else {
            Truth::Unknown
        }
    }
}

/// Knob overrides read from `[rules]`: a rule's threshold has a default in the rule and the
/// repository may override it by name.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Knobs {
    values: BTreeMap<String, u64>,
}

impl Knobs {
    /// No overrides.
    pub fn new() -> Self {
        Self::default()
    }

    /// Overrides `name` with `value`.
    #[must_use]
    pub fn with(mut self, name: &str, value: u64) -> Self {
        tracing::debug!(name, value, "knob override");
        self.values.insert(name.to_owned(), value);
        self
    }

    /// The value of `name`: the override if there is one, else `default`.
    pub fn get(&self, name: &str, default: u64) -> u64 {
        self.values.get(name).copied().unwrap_or(default)
    }

    /// The knob as a known count, for comparison against a [`Count`].
    pub fn limit(&self, name: &str, default: u64) -> Count {
        Count::exactly(self.get(name, default))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const OPS: [CmpOp; 6] = [
        CmpOp::Eq,
        CmpOp::Ne,
        CmpOp::Lt,
        CmpOp::Le,
        CmpOp::Gt,
        CmpOp::Ge,
    ];

    fn holds(op: CmpOp, a: u64, b: u64) -> bool {
        match op {
            CmpOp::Eq => a == b,
            CmpOp::Ne => a != b,
            CmpOp::Lt => a < b,
            CmpOp::Le => a <= b,
            CmpOp::Gt => a > b,
            CmpOp::Ge => a >= b,
        }
    }

    // frob:tests crates/gob-plan/src/exec/relations/count.rs::Count.compare
    #[test]
    fn interval_comparison_is_sound_against_every_concretisation() {
        let ivs: Vec<Count> = (0..4u64)
            .flat_map(|l| (l..5).map(move |h| Count { lo: l, hi: Some(h) }))
            .chain((0..3).map(|l| Count { lo: l, hi: None }))
            .collect();
        for &x in &ivs {
            for &y in &ivs {
                for op in OPS {
                    let t = x.compare(op, &y);
                    let (xh, yh) = (x.hi.unwrap_or(8), y.hi.unwrap_or(8));
                    let outcomes: Vec<bool> = (x.lo..=xh)
                        .flat_map(|a| (y.lo..=yh).map(move |b| holds(op, a, b)))
                        .collect();
                    match t {
                        Truth::Yes => assert!(outcomes.iter().all(|&o| o), "{x:?} {op:?} {y:?}"),
                        Truth::No => assert!(outcomes.iter().all(|&o| !o), "{x:?} {op:?} {y:?}"),
                        Truth::Unknown => {}
                    }
                }
            }
        }
    }

    #[test]
    fn unbounded_counts_never_decide_an_upper_bound() {
        let open = Count { lo: 1, hi: None };
        assert_eq!(open.compare(CmpOp::Gt, &Count::exactly(0)), Truth::Yes);
        assert_eq!(open.compare(CmpOp::Le, &Count::exactly(5)), Truth::Unknown);
        assert_eq!(open.compare(CmpOp::Gt, &Count::exactly(5)), Truth::Unknown);
    }

    // frob:tests crates/gob-plan/src/exec/relations/count.rs::Knobs.get
    #[test]
    fn a_knob_override_replaces_the_default() {
        let k = Knobs::new().with("max", 7);
        assert_eq!(k.get("max", 3), 7);
        assert_eq!(k.get("other", 3), 3);
    }
}
