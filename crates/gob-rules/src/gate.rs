//! Gate scopes (rules.md 6.1.5): which of `local | ci | release` a rule runs at.
//!
//! A rule declares `gates = [..]` on `#[rule]`; a repo may narrow or widen it with
//! `[rules.<id>] gates = [..]`. The severity is the same Error everywhere, only the scope differs.

// frob:ticket 01M5XMJHVMJH25WGPDQRC646Y4

use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};

use crate::decl::RuleDef;
use crate::nature::Nature;
use crate::registry::RuleSettings;

/// Where a check is being judged; chosen by `check --gate`.
#[derive(
    Debug, Clone, Copy, Default, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize,
)]
#[serde(rename_all = "kebab-case")]
pub enum Gate {
    /// A developer or agent run on a work tree (the default).
    #[default]
    Local,
    /// A continuous-integration run.
    Ci,
    /// The release (CD) step, where human sign-off blocks.
    Release,
}

/// Every gate, in widening order; the default scope of a rule that declares none.
pub const ALL_GATES: &[Gate] = &[Gate::Local, Gate::Ci, Gate::Release];

impl Gate {
    /// The lowercase spelling used by `--gate` and `gates = [..]`.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Local => "local",
            Self::Ci => "ci",
            Self::Release => "release",
        }
    }

    /// Parse `local`, `ci` or `release`; `None` for any other word.
    #[must_use]
    pub fn parse(word: &str) -> Option<Self> {
        ALL_GATES.iter().copied().find(|g| g.as_str() == word)
    }

    /// The gate a run is for: `explicit` when given, else `Ci` when `ci_env` (the value of `CI`) is `true` or `1`, else `Local`.
    #[must_use]
    pub fn resolve(explicit: Option<Self>, ci_env: Option<&str>) -> Self {
        let gate = explicit.unwrap_or(match ci_env {
            Some("true" | "1") => Self::Ci,
            _ => Self::Local,
        });
        tracing::debug!(
            gate = gate.as_str(),
            explicit = explicit.is_some(),
            "gate resolved"
        );
        gate
    }
}

/// The gates `def` runs at after `settings`: the repo's `[rules.<id>] gates` first, then the rule's own, else all three.
#[must_use]
pub fn gates_of(def: &RuleDef, settings: &RuleSettings) -> BTreeSet<Gate> {
    if let Some(set) = settings.gates.get(def.id) {
        return set.clone();
    }
    def.gates.unwrap_or(ALL_GATES).iter().copied().collect()
}

/// True when `def` runs (and can fail) at `gate`; a rule not in the gate is reported as "not in this gate", never clean or Unresolved.
#[must_use]
pub fn rule_in_gate(def: &RuleDef, settings: &RuleSettings, gate: Gate) -> bool {
    let inside = gates_of(def, settings).contains(&gate);
    tracing::trace!(rule = def.id, gate = gate.as_str(), inside, "rule_in_gate");
    inside
}

/// Refuse a repo `gates` override that narrows an Exact rule below `ci`, because CI must see everything that is not human sign-off.
///
/// # Errors
///
/// The message naming the rule when `nature` is Exact, `def` runs at `ci` by default and `gates` drops `ci`.
pub fn check_gate_override(
    def: &RuleDef,
    nature: Nature,
    gates: &BTreeSet<Gate>,
) -> Result<(), String> {
    let default_has_ci = def.gates.unwrap_or(ALL_GATES).contains(&Gate::Ci);
    if nature == Nature::Exact && default_has_ci && !gates.contains(&Gate::Ci) {
        tracing::warn!(
            rule = def.id,
            "gates override refused: exact rule narrowed below ci"
        );
        return Err(format!(
            "[rules.{}] gates may not drop \"ci\": CI must see every rule that is not human sign-off",
            def.id
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn def(gates: Option<&'static [Gate]>) -> RuleDef {
        RuleDef {
            id: "AAA001",
            gates,
            ..RuleDef::POISONED
        }
    }

    // frob:tests crates/gob-rules/src/gate.rs::rule_in_gate
    #[test]
    fn an_undeclared_rule_runs_at_every_gate() {
        let s = RuleSettings::default();
        for g in ALL_GATES {
            assert!(rule_in_gate(&def(None), &s, *g));
        }
    }

    // frob:tests crates/gob-rules/src/gate.rs::rule_in_gate
    #[test]
    fn a_release_only_rule_is_outside_local_and_ci() {
        let d = def(Some(&[Gate::Release]));
        let s = RuleSettings::default();
        assert!(!rule_in_gate(&d, &s, Gate::Local));
        assert!(!rule_in_gate(&d, &s, Gate::Ci));
        assert!(rule_in_gate(&d, &s, Gate::Release));
    }

    // frob:tests crates/gob-rules/src/gate.rs::gates_of
    #[test]
    fn a_repo_override_beats_the_rule_declaration() {
        let mut s = RuleSettings::default();
        s.gates
            .insert("AAA001".to_owned(), [Gate::Local, Gate::Release].into());
        let d = def(Some(&[Gate::Release]));
        assert!(rule_in_gate(&d, &s, Gate::Local));
        assert!(!rule_in_gate(&d, &s, Gate::Ci));
    }

    // frob:tests crates/gob-rules/src/gate.rs::resolve
    #[test]
    fn the_gate_is_explicit_then_ci_env_then_local() {
        assert_eq!(Gate::resolve(None, None), Gate::Local);
        assert_eq!(Gate::resolve(None, Some("true")), Gate::Ci);
        assert_eq!(Gate::resolve(None, Some("false")), Gate::Local);
        assert_eq!(
            Gate::resolve(Some(Gate::Release), Some("true")),
            Gate::Release
        );
        assert_eq!(Gate::parse("ci"), Some(Gate::Ci));
        assert_eq!(Gate::parse("nope"), None);
    }

    // frob:tests crates/gob-rules/src/gate.rs::check_gate_override
    #[test]
    fn narrowing_an_exact_rule_below_ci_is_refused_but_widening_is_not() {
        let d = def(None);
        let narrow: BTreeSet<Gate> = [Gate::Local].into();
        assert!(check_gate_override(&d, Nature::Exact, &narrow).is_err());
        assert!(check_gate_override(&d, Nature::Heuristic, &narrow).is_ok());
        let release_only = def(Some(&[Gate::Release]));
        let widen: BTreeSet<Gate> = [Gate::Local, Gate::Release].into();
        assert!(check_gate_override(&release_only, Nature::Exact, &widen).is_ok());
    }
}
