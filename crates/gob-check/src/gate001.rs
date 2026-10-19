// frob:ticket 01M3ZX7XGB7CP5M603DXV7331Q
//! GATE001 policy-weakened (`security.md` sections 2.7 and 4, I9).
//!
//! With `check --base REF` the effective policy is snapshotted at base and at
//! head (`gob_trust::policy`). This module is the pure comparison: it
//! classifies each changed setting as a weakening or not and emits one Error
//! finding per weakening, naming the old and new value. Strengthening is
//! silent. A weakening is cleared only by an exception carrying a ticket or a
//! reviewer label; the caller resolves that and passes the cleared keys in.
//!
//! Classification is by the dotted key family:
//!
//! | Key | Weakening when |
//! |---|---|
//! | `rules.*.severity`, `severity.*` | the severity rank drops (error > warn > advisory > off) |
//! | `rules.*.disabled`, `disable.*` | a rule is newly disabled |
//! | `fail_on*` | the failure threshold moves to a less strict level |
//! | `exclude*`, `grants`, `replaces`, `adapters`, `declaration.*` | something is added or the value changes |
//! | `packs`, `trust`, `compute`, anything else | the setting is removed or its value changes |

use std::collections::BTreeSet;

use gob_rules::{Finding, Severity};
use gob_trust::policy::{PolicyChange, PolicyDelta};
use tracing::{debug, trace, warn};

/// Rule id of the policy-weakened gate.
pub const GATE001: &str = "GATE001";

/// One policy setting that got weaker between base and head.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Weakening {
    /// Dotted key of the weakened setting.
    pub key: String,
    /// Canonical value at base, `None` when it did not exist.
    pub old: Option<String>,
    /// Canonical value at head, `None` when it was removed.
    pub new: Option<String>,
}

impl Weakening {
    /// The message naming the key and its old and new value.
    #[must_use]
    pub fn message(&self) -> String {
        let show = |v: &Option<String>| v.clone().unwrap_or_else(|| "(unset)".to_owned());
        format!(
            "policy weakened: {} changed from {} to {}",
            self.key,
            show(&self.old),
            show(&self.new)
        )
    }
}

fn unquote(v: &str) -> &str {
    v.trim().trim_matches('"')
}

/// Severity rank: higher is stricter; `None` for an unknown token.
fn severity_rank(v: &str) -> Option<u8> {
    match unquote(v) {
        "off" | "none" | "allow" | "ignore" => Some(0),
        "advisory" | "info" => Some(1),
        "warn" | "warning" => Some(2),
        "error" | "deny" => Some(3),
        _ => None,
    }
}

/// `fail_on` threshold rank: higher means fewer severities fail the gate.
fn threshold_rank(v: &str) -> Option<u8> {
    match unquote(v) {
        "advisory" | "info" => Some(1),
        "warn" | "warning" => Some(2),
        "error" => Some(3),
        "never" | "none" | "off" => Some(4),
        _ => None,
    }
}

fn string_items(v: &str) -> Option<BTreeSet<String>> {
    let table: toml::Table = format!("v = {v}").parse().ok()?;
    let arr = table.get("v")?.as_array()?;
    Some(
        arr.iter()
            .map(|e| e.as_str().map_or_else(|| e.to_string(), str::to_owned))
            .collect(),
    )
}

/// True when the new value adds an item the old one lacked (or is not comparable).
fn adds_items(old: Option<&str>, new: &str) -> bool {
    match (old.and_then(string_items), string_items(new)) {
        (Some(o), Some(n)) => n.difference(&o).next().is_some(),
        _ => true,
    }
}

fn is_loosening_family(key: &str) -> bool {
    let root = key.split('.').next().unwrap_or(key);
    matches!(
        root,
        "exclude" | "excludes" | "grants" | "replaces" | "adapters" | "declaration"
    )
}

/// Whether `change` makes policy weaker (conservative for unknown shapes).
fn is_weakening(change: &PolicyChange) -> bool {
    let key = change.key.as_str();
    let old = change.old.as_deref();
    let new = change.new.as_deref();
    let last = key.rsplit('.').next().unwrap_or(key);
    let root = key.split('.').next().unwrap_or(key);

    if last == "severity" || root == "severity" {
        return match (old.and_then(severity_rank), new.and_then(severity_rank)) {
            (Some(o), Some(n)) => n < o,
            (None, _) if old.is_none() => new.is_some_and(|n| severity_rank(n) != Some(3)),
            _ => new.is_none() || old != new,
        };
    }
    if last == "disabled" || root == "disable" {
        let on = |v: Option<&str>| v.is_some_and(|v| unquote(v) != "false");
        return on(new) && !on(old);
    }
    if root.starts_with("fail_on") {
        return match (old.and_then(threshold_rank), new.and_then(threshold_rank)) {
            (Some(o), Some(n)) => n > o,
            _ => new.is_none() || old != new,
        };
    }
    if is_loosening_family(key) {
        return match new {
            None => false,
            Some(n) => old.is_none() || (old != Some(n) && adds_items(old, n)),
        };
    }
    old.is_some() && old != new
}

/// Every weakening in `delta`, in key order.
#[must_use]
pub fn weakenings(delta: &PolicyDelta) -> Vec<Weakening> {
    delta
        .changes
        .iter()
        .filter(|c| {
            let weak = is_weakening(c);
            if weak {
                debug!(key = %c.key, "policy weakening");
            } else {
                trace!(key = %c.key, "policy change is not a weakening");
            }
            weak
        })
        .map(|c| Weakening {
            key: c.key.clone(),
            old: c.old.clone(),
            new: c.new.clone(),
        })
        .collect()
}

/// One GATE001 Error finding per weakening in `delta` not named in `cleared`.
///
/// `cleared` holds the keys an exception with a ticket or reviewer label
/// covers; those are skipped. Strengthening never produces a finding.
#[must_use]
pub fn gate001_findings(delta: &PolicyDelta, cleared: &BTreeSet<String>) -> Vec<Finding> {
    weakenings(delta)
        .into_iter()
        .filter(|w| {
            let skip = cleared.contains(&w.key);
            if skip {
                debug!(key = %w.key, "GATE001 cleared by an exception");
            }
            !skip
        })
        .filter_map(|w| {
            let msg = w.message();
            warn!(key = %w.key, "GATE001 policy-weakened");
            let rule = GATE001.parse().ok()?;
            Some(Finding::new(rule, Severity::Error, None, msg, &w.key))
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_trust::policy::PolicySnapshot;

    fn delta(base: &str, head: &str) -> PolicyDelta {
        let b = PolicySnapshot::from_toml(base).unwrap();
        let h = PolicySnapshot::from_toml(head).unwrap();
        b.diff(&h)
    }

    fn run(base: &str, head: &str) -> Vec<Finding> {
        gate001_findings(&delta(base, head), &BTreeSet::new())
    }

    // frob:tests crates/gob-check/src/gate001.rs::gate001_findings
    #[test]
    fn severity_error_to_warn_names_old_and_new() {
        let got = run(
            "[rules.SEC001]\nseverity = \"error\"\n",
            "[rules.SEC001]\nseverity = \"warn\"\n",
        );
        assert_eq!(got.len(), 1);
        let m = &got[0].message;
        assert!(
            m.contains("rules.SEC001.severity")
                && m.contains("\"error\"")
                && m.contains("\"warn\"")
        );
        assert_eq!(got[0].severity, Severity::Error);
        assert_eq!(got[0].rule.to_string(), "GATE001");
    }

    // frob:tests crates/gob-check/src/gate001.rs::gate001_findings
    #[test]
    fn strengthening_policy_is_silent() {
        let got = run(
            "fail_on = \"error\"\n[rules.SEC001]\nseverity = \"warn\"\ndisabled = true\n[exclude]\npaths = [\"a\", \"b\"]\n",
            "fail_on = \"warn\"\n[rules.SEC001]\nseverity = \"error\"\ndisabled = false\n[exclude]\npaths = [\"a\"]\n",
        );
        assert!(got.is_empty(), "{got:?}");
    }

    // frob:tests crates/gob-check/src/gate001.rs::weakenings
    #[test]
    fn disable_exclude_and_threshold_are_weakenings() {
        let w = weakenings(&delta(
            "fail_on = \"error\"\n[exclude]\npaths = [\"a\"]\n",
            "fail_on = \"never\"\n[exclude]\npaths = [\"a\", \"b\"]\n[rules.X]\ndisabled = true\n",
        ));
        let keys: Vec<&str> = w.iter().map(|w| w.key.as_str()).collect();
        assert_eq!(keys, ["exclude.paths", "fail_on", "rules.X.disabled"]);
    }

    // frob:tests crates/gob-check/src/gate001.rs::gate001_findings
    #[test]
    fn exception_clears_a_weakening() {
        let d = delta(
            "[rules.SEC001]\nseverity = \"error\"\n",
            "[rules.SEC001]\nseverity = \"warn\"\n",
        );
        let cleared = BTreeSet::from(["rules.SEC001.severity".to_owned()]);
        assert!(gate001_findings(&d, &cleared).is_empty());
    }

    // frob:tests crates/gob-check/src/gate001.rs::weakenings
    #[test]
    fn removed_pack_is_weakened_added_pack_is_not() {
        let w = weakenings(&delta("[packs]\nx = 1\n", "[packs]\n"));
        assert_eq!(w.len(), 1);
        assert!(weakenings(&delta("", "[packs]\nx = 1\n")).is_empty());
    }
}
