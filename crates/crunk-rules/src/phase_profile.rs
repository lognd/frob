//! The lint profile a project phase selects (design `crunk.md` section 8, first row).
//!
//! - `discovery` and `alpha`: structure lints only; HUMAN001 and the whole A11Y set are not
//!   applicable.
//! - `beta`: everything except the live-only metrics and experiment rules, so the full A11Y set
//!   and HUMAN001 run.
//! - `live`: everything, metrics and experiments included.
//!
//! The profile is a default: a rule the project names in `[lint]` runs (or is switched off) as
//! the project says, whatever the phase. Without a phase the project is treated as `beta` and the
//! report says so.

// frob:ticket 01M5XCYCP797Z6M8WPBW7FAD5W

use crunk_spec::{DesignSpec, Phase, ResolvedPhase};

/// Families whose lints check structure and so run in every phase.
pub const STRUCTURE_FAMILIES: &[&str] = &[
    "TOKEN", "TOKENS", "ORG", "WAIVE", "SCENE", "COMP", "STATE", "UX", "PORT",
];

/// Families that only run once a project is `live`: post-launch metrics and experiments.
pub const LIVE_ONLY_FAMILIES: &[&str] = &["METRIC", "EXPERIMENT"];

/// Why a rule does not run under a phase profile.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Skip {
    /// The phase is too early for this rule; the payload is the earliest phase that runs it.
    TooEarly(Phase),
}

/// The family prefix of a rule id, e.g. `A11Y` for `A11Y003`.
fn prefix(rule_id: &str) -> &str {
    rule_id.trim_end_matches(|c: char| c.is_ascii_digit())
}

/// The earliest phase that runs `rule_id` by default.
pub fn earliest_phase(rule_id: &str) -> Phase {
    let family = prefix(rule_id);
    if STRUCTURE_FAMILIES.contains(&family) {
        Phase::Discovery
    } else if LIVE_ONLY_FAMILIES.contains(&family) {
        Phase::Live
    } else {
        Phase::Beta
    }
}

/// Whether the profile of `phase` runs `rule_id`, ignoring any `[lint]` override.
///
/// # Errors
///
/// [`Skip::TooEarly`] when `phase` is before the earliest phase that runs the rule.
pub fn profile_runs(phase: Phase, rule_id: &str) -> Result<(), Skip> {
    let earliest = earliest_phase(rule_id);
    if phase >= earliest {
        Ok(())
    } else {
        Err(Skip::TooEarly(earliest))
    }
}

/// Whether `rule_id` runs under `phase` for `spec`: an explicit `[lint]` entry overrides the
/// profile (the rule runs, at the severity `[lint]` gives, or is off as usual).
///
/// # Errors
///
/// [`Skip::TooEarly`] when the profile skips the rule and `[lint]` does not name it.
pub fn runs(spec: &DesignSpec, phase: Phase, rule_id: &str) -> Result<(), Skip> {
    if spec.lint.rules.contains_key(rule_id) {
        tracing::debug!(rule = rule_id, %phase, "[lint] overrides the phase profile");
        return Ok(());
    }
    let verdict = profile_runs(phase, rule_id);
    if verdict.is_err() {
        tracing::debug!(rule = rule_id, %phase, "rule not applicable in this phase");
    }
    verdict
}

/// What the phase profile did to one check run, for the envelope.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProfileReport {
    /// The phase and whether it was declared or defaulted.
    pub resolved: ResolvedPhase,
    /// The rule ids listed as not applicable, in the order given.
    pub not_applicable: Vec<String>,
}

impl ProfileReport {
    /// The envelope lines: the phase note, then the not-applicable rules when there are any.
    pub fn lines(&self) -> Vec<String> {
        let mut lines = vec![self.resolved.note()];
        if !self.not_applicable.is_empty() {
            lines.push(format!(
                "not applicable in phase {}: {}",
                self.resolved.phase,
                self.not_applicable.join(", ")
            ));
        }
        lines
    }
}

/// Apply the profile to `rule_ids`: the report lists every rule that does not run.
pub fn report<'a>(
    spec: &DesignSpec,
    resolved: ResolvedPhase,
    rule_ids: impl IntoIterator<Item = &'a str>,
) -> ProfileReport {
    let not_applicable: Vec<String> = rule_ids
        .into_iter()
        .filter(|id| runs(spec, resolved.phase, id).is_err())
        .map(str::to_owned)
        .collect();
    tracing::info!(phase = %resolved.phase, defaulted = resolved.defaulted, skipped = not_applicable.len(), "phase profile applied");
    ProfileReport {
        resolved,
        not_applicable,
    }
}
