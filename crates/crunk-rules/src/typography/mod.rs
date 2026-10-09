//! The typography judgments shared by TYPE002 and TYPE003 (port of `crunk/rules/_typography.py`):
//! reading a `font-family` stack, the stacks a project declares, and the numeric weight of a
//! `font-weight` value.

// frob:ticket 01M43ATBDWVSJBXP7TEQ6DBW3W

use std::collections::BTreeMap;

use crunk_spec::DesignSpec;

/// `normal` and `bold` resolve to fixed numeric weights.
const KEYWORD_WEIGHTS: &[(&str, i64)] = &[("normal", 400), ("bold", 700)];

/// Keywords with no fixed numeric weight: relative (`bolder`, `lighter`) or inherited. Exempt.
const EXEMPT_KEYWORDS: &[&str] = &[
    "bolder",
    "lighter",
    "inherit",
    "initial",
    "unset",
    "revert",
    "revert-layer",
];

/// A `font-family` value as lowercase, quote-stripped member names, empty members dropped.
pub fn split_family_stack(value: &str) -> Vec<String> {
    value
        .split(',')
        .map(|part| part.trim().trim_matches(['"', '\'']).to_lowercase())
        .filter(|part| !part.is_empty())
        .collect()
}

/// The named stacks TYPE002 checks against, lowercased: the declared `[typography.stacks]` when
/// there are any, else the single implicit stack of `families` (keyed `<families>`).
pub fn effective_stacks(spec: &DesignSpec) -> BTreeMap<String, Vec<String>> {
    let lowered = |members: &[String]| members.iter().map(|m| m.to_lowercase()).collect();
    if spec.typography.stacks.is_empty() {
        return BTreeMap::from([("<families>".to_owned(), lowered(&spec.typography.families))]);
    }
    spec.typography
        .stacks
        .iter()
        .map(|(name, members)| (name.clone(), lowered(members)))
        .collect()
}

/// What a `font-weight` value means for TYPE003.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Weight {
    /// A numeric weight (`bold` is 700, `normal` 400).
    Numeric(i64),
    /// A relative or inherited keyword: nothing fixed to check.
    Exempt,
    /// Text that is not a weight (a `var()`, a number with a unit): skipped.
    Unparseable,
}

/// The weight `value` names.
pub fn weight_of(value: &str) -> Weight {
    let raw = value.trim().to_lowercase();
    if EXEMPT_KEYWORDS.contains(&raw.as_str()) {
        return Weight::Exempt;
    }
    if let Some((_, weight)) = KEYWORD_WEIGHTS.iter().find(|(keyword, _)| *keyword == raw) {
        return Weight::Numeric(*weight);
    }
    raw.parse::<i64>()
        .map_or(Weight::Unparseable, Weight::Numeric)
}
