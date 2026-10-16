//! Edits, fixes, tiers and the deterministic overlap-resolving planner.

use gob_rules::Applicability;

/// One byte-range replacement in one file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Edit {
    /// Path of the file the edit applies to.
    pub path: String,
    /// First byte replaced.
    pub start: usize,
    /// One past the last byte replaced (`start == end` is a pure insertion).
    pub end: usize,
    /// Text written in place of the range.
    pub replacement: String,
}

impl Edit {
    /// Whether this edit's span intersects `other`'s in the same file.
    #[must_use]
    pub fn overlaps(&self, other: &Edit) -> bool {
        self.path == other.path
            && ((self.start < other.end && other.start < self.end)
                || (self.start == self.end
                    && other.start == other.end
                    && self.start == other.start))
    }
}

/// A rule's proposed change: one or more edits applied together or not at all.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Fix {
    /// Id of the rule that proposed the fix.
    pub rule: String,
    /// Human title of the fix.
    pub title: String,
    /// How far the fix can be trusted without a human.
    pub applicability: Applicability,
    /// The edits that make up the fix.
    pub edits: Vec<Edit>,
}

/// Which applicability tiers a run may apply (A is the safest).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Tier {
    /// Tier A: machine-applicable fixes only.
    A,
    /// Tier B: A plus maybe-incorrect fixes.
    B,
    /// Tier C: B plus fixes that still carry placeholders.
    C,
}

impl Tier {
    /// Whether a fix of `applicability` may be applied at this tier.
    #[must_use]
    pub const fn admits(self, applicability: Applicability) -> bool {
        match applicability {
            Applicability::Machine => true,
            Applicability::MaybeIncorrect => matches!(self, Self::B | Self::C),
            Applicability::HasPlaceholders => matches!(self, Self::C),
            Applicability::Manual => false,
        }
    }
}

/// Why a fix did not make it into the plan.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DropReason {
    /// An edit overlapped an earlier accepted fix.
    Overlap {
        /// Rule of the fix that won the span.
        winner_rule: String,
        /// The loser's conflicting edit.
        edit: Edit,
    },
    /// An edit has start after end, or the fix's own edits overlap each other.
    Invalid,
    /// The applicability is above the requested tier, or has no edits.
    Tier,
}

/// A fix the planner refused, with the rule and span that explain it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Dropped {
    /// The dropped fix.
    pub fix: Fix,
    /// Why it was dropped.
    pub reason: DropReason,
}

/// The accepted fixes (deterministic order) and everything dropped.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Plan {
    /// Fixes to apply, ordered by first edit position.
    pub accepted: Vec<Fix>,
    /// Fixes refused, in planning order.
    pub dropped: Vec<Dropped>,
}

fn sort_key(f: &Fix) -> (String, usize, usize, String, String) {
    let first = f
        .edits
        .iter()
        .min_by_key(|e| (e.path.as_str(), e.start, e.end));
    let (path, start, end) =
        first.map_or((String::new(), 0, 0), |e| (e.path.clone(), e.start, e.end));
    (path, start, end, f.rule.clone(), f.title.clone())
}

fn self_consistent(f: &Fix) -> bool {
    f.edits.iter().all(|e| e.start <= e.end)
        && f.edits
            .iter()
            .enumerate()
            .all(|(i, a)| f.edits[i + 1..].iter().all(|b| !a.overlaps(b)))
}

/// Choose the fixes to apply: earlier span wins, losers are returned with rule and span.
#[must_use]
pub fn plan(fixes: Vec<Fix>, tier: Tier) -> Plan {
    let mut fixes = fixes;
    fixes.sort_by_cached_key(sort_key);
    let mut out = Plan::default();
    for fix in fixes {
        let reason = if fix.edits.is_empty() || !tier.admits(fix.applicability) {
            Some(DropReason::Tier)
        } else if !self_consistent(&fix) {
            Some(DropReason::Invalid)
        } else {
            fix.edits.iter().find_map(|e| {
                out.accepted.iter().find_map(|w| {
                    w.edits
                        .iter()
                        .any(|we| we.overlaps(e))
                        .then(|| DropReason::Overlap {
                            winner_rule: w.rule.clone(),
                            edit: e.clone(),
                        })
                })
            })
        };
        if let Some(reason) = reason {
            tracing::info!(rule = %fix.rule, ?reason, "fix dropped from plan");
            out.dropped.push(Dropped { fix, reason });
        } else {
            tracing::debug!(rule = %fix.rule, edits = fix.edits.len(), "fix accepted");
            out.accepted.push(fix);
        }
    }
    out
}
