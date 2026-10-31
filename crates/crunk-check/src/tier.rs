//! Check tiers (crunk.md section 4, D112): which rules a `--tier` run decides, and the report of
//! those it did not.
//!
//! A rule's declared tier is the lowest tier of its family row ([`crunk_rules::family`]); a rule
//! of an unknown family declares `T0`. A run up to tier `N` keeps the findings of rules declared
//! at `N` or below. Every other rule is listed in [`NotRun`], stable-ordered by rule id, so the
//! gap is visible: a rule that could not run is never reported as clean. A `must_measure` rule
//! above the tier is [`NotRunStatus::Unresolved`] (silence is not a pass); the rest are
//! [`NotRunStatus::NotRun`]. Not-run entries never touch the exit code.

// frob:ticket 01M5XCXV02ZVYV71DFY08R5Y3H

use std::fmt;
use std::str::FromStr;

use crunk_rules::family::{CheckTier, family};
use gob_rules::{Finding, RuleDef};
use serde::Serialize;
use serde_json::{Value, json};

/// The tiers `--tier` accepts, for the unknown-tier message.
pub const TIER_NAMES: &str = "T0, T1, T2, T3, T4";

/// A check tier, ordered from cheapest (static) to dearest (human).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize)]
pub enum Tier {
    /// Static: the files alone.
    T0,
    /// Layout solve.
    T1,
    /// Render.
    T2,
    /// Live browser or editor.
    T3,
    /// A person.
    T4,
}

impl Default for Tier {
    /// `T1`: the default locally and in PR CI.
    fn default() -> Self {
        Self::T1
    }
}

impl Tier {
    /// `T0` to `T4`.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::T0 => "T0",
            Self::T1 => "T1",
            Self::T2 => "T2",
            Self::T3 => "T3",
            Self::T4 => "T4",
        }
    }

    /// What a rule of this tier needs, as the reason it did not run below it.
    pub const fn needs(self) -> &'static str {
        match self {
            Self::T0 => "the files alone",
            Self::T1 => "the layout solver",
            Self::T2 => "rendered pixels",
            Self::T3 => "a live browser or the Unity editor",
            Self::T4 => "a person",
        }
    }
}

impl fmt::Display for Tier {
    /// Writes `T0` to `T4`.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// A `--tier` value that is not one of `T0` to `T4`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnknownTier(pub String);

impl fmt::Display for UnknownTier {
    /// Names the bad value and lists the valid tiers.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "unknown tier {:?}; expected one of {TIER_NAMES}", self.0)
    }
}

impl std::error::Error for UnknownTier {}

impl FromStr for Tier {
    type Err = UnknownTier;

    /// Parse `T0` to `T4`, case-insensitively.
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_ascii_uppercase().as_str() {
            "T0" => Ok(Self::T0),
            "T1" => Ok(Self::T1),
            "T2" => Ok(Self::T2),
            "T3" => Ok(Self::T3),
            "T4" => Ok(Self::T4),
            _ => {
                tracing::warn!(value = s, "unknown check tier");
                Err(UnknownTier(s.to_owned()))
            }
        }
    }
}

impl From<CheckTier> for Tier {
    /// The family-row tier as the CLI tier.
    fn from(t: CheckTier) -> Self {
        match t {
            CheckTier::T0 => Self::T0,
            CheckTier::T1 => Self::T1,
            CheckTier::T2 => Self::T2,
            CheckTier::T3 => Self::T3,
        }
    }
}

/// The tier a rule declares: the lowest tier of its family, `T0` when the family is unknown.
pub fn rule_tier(def: &RuleDef) -> Tier {
    family(def.family)
        .and_then(|f| f.tiers.iter().copied().min())
        .map_or(Tier::T0, Tier::from)
}

/// Why a rule above the tier produced nothing.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NotRunStatus {
    /// The rule did not run.
    NotRun,
    /// A `must_measure` rule did not run: its silence decides nothing.
    Unresolved,
}

/// One rule a run did not decide.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct NotRun {
    /// Rule id.
    pub rule: String,
    /// Family prefix.
    pub family: String,
    /// The tier the rule declares.
    pub tier: Tier,
    /// The tier the run went up to.
    pub ran_to: Tier,
    /// Not run, or unresolved for a `must_measure` rule.
    pub status: NotRunStatus,
    /// One line on why.
    pub reason: String,
}

/// Whether the `--only` names select a rule (empty keeps everything).
fn selected(only: &[String], def: &RuleDef) -> bool {
    only.is_empty() || only.iter().any(|o| o == def.family || o == def.id)
}

/// The rules of `defs` above `ran_to` that `only` selects, sorted by rule id.
pub fn not_run<'a>(
    defs: impl IntoIterator<Item = &'a RuleDef>,
    ran_to: Tier,
    only: &[String],
) -> Vec<NotRun> {
    let mut out: Vec<NotRun> = defs
        .into_iter()
        .filter(|d| selected(only, d))
        .filter_map(|d| {
            let tier = rule_tier(d);
            (tier > ran_to).then(|| NotRun {
                rule: d.id.to_owned(),
                family: d.family.to_owned(),
                tier,
                ran_to,
                status: if d.must_measure {
                    NotRunStatus::Unresolved
                } else {
                    NotRunStatus::NotRun
                },
                reason: format!(
                    "declared {tier}, needs {}; this run decides up to {ran_to}",
                    tier.needs()
                ),
            })
        })
        .collect();
    out.sort_by(|a, b| a.rule.cmp(&b.rule));
    out.dedup_by(|a, b| a.rule == b.rule);
    tracing::info!(ran_to = %ran_to, not_run = out.len(), "rules above the tier listed as not run");
    out
}

/// Drop the findings of rules above the tier (they cannot be decided there) from `findings`.
pub fn retain_decided(findings: &mut Vec<Finding>, skipped: &[NotRun]) {
    let before = findings.len();
    findings.retain(|f| !skipped.iter().any(|n| n.rule == f.rule.as_str()));
    tracing::debug!(
        dropped = before - findings.len(),
        "findings of above-tier rules dropped"
    );
}

/// The `not_run` section of the check document.
pub fn section(ran_to: Tier, skipped: &[NotRun]) -> Value {
    json!({ "tier": ran_to, "rules": skipped })
}
