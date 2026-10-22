//! Counts as intervals, interval comparison, and knob overrides (grl-spec.md 7.0.2, 7.1).
//!
//! `count(x: SRC where c)` denotes `[l, h]`: `l` counts the members for which the condition is
//! certainly true, `h` those for which it is not certainly false, and `h` is unbounded when the
//! domain is open. Only interval comparison is offered on counts: a non-monotone predicate
//! ("count is even") at the endpoints of an interval is unsound (Ross and Sagiv 1992).

use std::collections::BTreeMap;

use gob_ir::Truth;

use crate::plan::{CmpOp, Scale};

/// An interval `[lo, hi]` of counts; `hi` is `None` for unbounded (an open domain).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Count {
    /// The members certainly counted.
    pub lo: u64,
    /// The members possibly counted; `None` is unbounded.
    pub hi: Option<u64>,
}

/// An interval of exact integers; `i128::MIN` and `i128::MAX` stand for the infinities.
#[derive(Debug, Clone, Copy)]
struct Span {
    lo: i128,
    hi: i128,
}

impl Span {
    /// The counts in `c`, each multiplied by `factor` (a negative factor flips the interval).
    fn of(c: &Count, factor: i128) -> Self {
        let lo = i128::from(c.lo);
        let hi = c.hi.map(i128::from);
        match factor.signum() {
            0 => Self { lo: 0, hi: 0 },
            1 => Self {
                lo: lo * factor,
                hi: hi.map_or(i128::MAX, |h| h * factor),
            },
            _ => Self {
                lo: hi.map_or(i128::MIN, |h| h * factor),
                hi: lo * factor,
            },
        }
    }

    /// `self < other` (strict) or `self <= other`, three-valued.
    fn less(&self, other: &Self, strict: bool) -> Truth {
        let (yes, no) = if strict {
            (self.hi < other.lo, other.hi <= self.lo)
        } else {
            (self.hi <= other.lo, other.hi < self.lo)
        };
        if yes {
            Truth::Yes
        } else if no {
            Truth::No
        } else {
            Truth::Unknown
        }
    }

    /// `self == other`: Yes only for four equal finite endpoints, No for disjoint intervals.
    fn equal(&self, other: &Self) -> Truth {
        if self.lo == self.hi && other.lo == other.hi && self.lo == other.lo {
            Truth::Yes
        } else if self.hi < other.lo || other.hi < self.lo {
            Truth::No
        } else {
            Truth::Unknown
        }
    }

    /// Kleene comparison under `op`.
    fn compare(&self, op: CmpOp, other: &Self) -> Truth {
        match op {
            CmpOp::Lt => self.less(other, true),
            CmpOp::Le => self.less(other, false),
            CmpOp::Gt => other.less(self, true),
            CmpOp::Ge => other.less(self, false),
            CmpOp::Eq => self.equal(other),
            CmpOp::Ne => !self.equal(other),
        }
    }
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
        self.compare_scaled(Scale::ONE, op, other, Scale::ONE)
    }

    /// Kleene comparison of `self * lhs_scale` with `other * rhs_scale`, exactly (no rounding).
    ///
    /// Both sides are multiplied by `10^(places of both)` so the comparison is over integers; a
    /// zero scale pins its side to zero even when the count is unbounded, and a negative scale
    /// flips the interval (an unbounded count then reaches minus infinity).
    pub fn compare_scaled(
        &self,
        lhs_scale: Scale,
        op: CmpOp,
        other: &Self,
        rhs_scale: Scale,
    ) -> Truth {
        let pow = |places: u8| 10i128.pow(u32::from(places));
        let lf = i128::from(lhs_scale.num) * pow(rhs_scale.places);
        let rf = i128::from(rhs_scale.num) * pow(lhs_scale.places);
        Span::of(self, lf).compare(op, &Span::of(other, rf))
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

    /// Whether `a * l  op  b * r` holds exactly, by cross-multiplying out the decimal places.
    fn scaled_holds(op: CmpOp, a: u64, l: Scale, b: u64, r: Scale) -> bool {
        let lhs = i128::from(a) * i128::from(l.num) * 10i128.pow(u32::from(r.places));
        let rhs = i128::from(b) * i128::from(r.num) * 10i128.pow(u32::from(l.places));
        match op {
            CmpOp::Eq => lhs == rhs,
            CmpOp::Ne => lhs != rhs,
            CmpOp::Lt => lhs < rhs,
            CmpOp::Le => lhs <= rhs,
            CmpOp::Gt => lhs > rhs,
            CmpOp::Ge => lhs >= rhs,
        }
    }

    // frob:ticket 01M5GA77VTC3VDYVZ2HBZNRM2K
    // frob:tests crates/gob-plan/src/exec/relations/count.rs::Count.compare_scaled
    #[test]
    fn scaled_comparison_is_sound_for_negative_zero_and_fractional_scales() {
        let scales = [
            Scale::ONE,
            Scale { num: 0, places: 0 },
            Scale { num: 0, places: 3 },
            Scale { num: 5, places: 1 },
            Scale { num: 75, places: 2 },
            Scale { num: 3, places: 0 },
            Scale { num: -1, places: 0 },
            Scale {
                num: -25,
                places: 2,
            },
        ];
        let ivs: Vec<Count> = (0..3u64)
            .flat_map(|l| (l..4).map(move |h| Count { lo: l, hi: Some(h) }))
            .chain((0..3).map(|l| Count { lo: l, hi: None }))
            .collect();
        for &x in &ivs {
            for &y in &ivs {
                for &sx in &scales {
                    for &sy in &scales {
                        for op in OPS {
                            let t = x.compare_scaled(sx, op, &y, sy);
                            let (xh, yh) = (x.hi.unwrap_or(8), y.hi.unwrap_or(8));
                            let outcomes: Vec<bool> = (x.lo..=xh)
                                .flat_map(|a| {
                                    (y.lo..=yh).map(move |b| scaled_holds(op, a, sx, b, sy))
                                })
                                .collect();
                            let ctx = format!("{x:?}*{sx:?} {op:?} {y:?}*{sy:?}");
                            match t {
                                Truth::Yes => assert!(outcomes.iter().all(|&o| o), "{ctx}"),
                                Truth::No => assert!(outcomes.iter().all(|&o| !o), "{ctx}"),
                                Truth::Unknown => {}
                            }
                        }
                    }
                }
            }
        }
    }

    // frob:ticket 01M5GA77VTC3VDYVZ2HBZNRM2K
    // frob:tests crates/gob-plan/src/exec/relations/count.rs::Count.compare_scaled
    #[test]
    fn scaling_decides_exact_counts_and_a_zero_scale_pins_an_open_count() {
        let half = Scale { num: 5, places: 1 };
        // 2 >= 0.5 * 4 holds; 1 >= 0.5 * 4 does not.
        assert_eq!(
            Count::exactly(2).compare_scaled(Scale::ONE, CmpOp::Ge, &Count::exactly(4), half),
            Truth::Yes
        );
        assert_eq!(
            Count::exactly(1).compare_scaled(Scale::ONE, CmpOp::Ge, &Count::exactly(4), half),
            Truth::No
        );
        // Zero counts: 0 >= 0.5 * 0 holds, 0 > 0.5 * 0 does not.
        let zero = Count::exactly(0);
        assert_eq!(
            zero.compare_scaled(Scale::ONE, CmpOp::Ge, &zero, half),
            Truth::Yes
        );
        assert_eq!(
            zero.compare_scaled(Scale::ONE, CmpOp::Gt, &zero, half),
            Truth::No
        );
        // An open count times zero is exactly zero, so the comparison is decided.
        let open = Count { lo: 0, hi: None };
        let none = Scale { num: 0, places: 2 };
        assert_eq!(
            open.compare_scaled(none, CmpOp::Eq, &zero, Scale::ONE),
            Truth::Yes
        );
        // A negative scale flips the interval: -1 * open <= 0.
        let neg = Scale { num: -1, places: 0 };
        assert_eq!(
            open.compare_scaled(neg, CmpOp::Le, &zero, Scale::ONE),
            Truth::Yes
        );
    }

    // frob:tests crates/gob-plan/src/exec/relations/count.rs::Knobs.get
    #[test]
    fn a_knob_override_replaces_the_default() {
        let k = Knobs::new().with("max", 7);
        assert_eq!(k.get("max", 3), 7);
        assert_eq!(k.get("other", 3), 3);
    }
}
