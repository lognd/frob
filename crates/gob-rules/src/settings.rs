//! `[rules]` config reading and per-product disabled-rule filtering; ramp-in is retired (rules.md 6.1.3).

// frob:ticket 01M4HDXVZNXTNANMHRGVGQ66DC
use std::collections::BTreeSet;

use crate::finding::Finding;
use crate::gate::Gate;
use crate::meta::Severity;
use crate::registry::RuleSettings;

/// A parsed `major.minor.patch` triple; a pre-release or build suffix is dropped.
fn triple(text: &str) -> Option<(u64, u64, u64)> {
    let core = text.split(['-', '+']).next()?;
    let mut parts = core.split('.').map(str::parse::<u64>);
    let major = parts.next()?.ok()?;
    let minor = parts.next()?.ok()?;
    let patch = parts.next()?.ok()?;
    parts.next().is_none().then_some((major, minor, patch))
}

/// True when `current` is inside the minor line a rule first shipped in (`since` `0.532.0` matches `0.532.x`); false when either is not a version.
#[must_use]
pub fn shipped_in(since: &str, current: &str) -> bool {
    let (Some(first), Some(now)) = (triple(since), triple(current)) else {
        return false;
    };
    now >= first && (now.0, now.1) == (first.0, first.1)
}

/// The config error for a retired `severity` spelling, naming its replacement.
fn retired_severity(id: &str, word: &str) -> String {
    format!(
        "[rules.{id}] severity = \"{word}\" is no longer supported: use \"error\" plus a baseline in frob-baseline.toml, or \"off\""
    )
}

/// The gate set of `[rules.<id>] gates = [..]`, or the config error naming the bad word.
fn parse_gates(id: &str, items: &[toml::Value]) -> Result<BTreeSet<Gate>, String> {
    let mut out = BTreeSet::new();
    for item in items {
        let word = item.as_str().unwrap_or_default();
        let gate = Gate::parse(word).ok_or_else(|| {
            format!("[rules.{id}] gates names `{item}`: expected local, ci or release")
        })?;
        out.insert(gate);
    }
    if out.is_empty() {
        return Err(format!(
            "[rules.{id}] gates is empty: name at least one of local, ci, release (or set severity = \"off\")"
        ));
    }
    Ok(out)
}

impl RuleSettings {
    /// Read the `[rules.<id>] severity` (`error` or `off`) ids and `disabled = true` ids from the `text` of a product config; a missing `[rules]` gives the defaults.
    ///
    /// # Errors
    ///
    /// The TOML parse error when `text` is not TOML, or the message naming `error` plus a baseline, or `off`, when a severity is `warn` or `advisory`.
    pub fn from_toml(text: &str) -> Result<Self, String> {
        let doc: toml::Table = text.parse().map_err(|e: toml::de::Error| e.to_string())?;
        let mut out = Self::default();
        let Some(toml::Value::Table(rules)) = doc.get("rules") else {
            return Ok(out);
        };
        for (key, value) in rules {
            match (key.as_str(), value) {
                ("ramp", _) => {
                    tracing::warn!(
                        "[rules] ramp is deprecated and ignored: ramp-in is retired, a new rule ships as an error"
                    );
                }
                (id, toml::Value::Table(entry)) => {
                    match entry.get("severity").and_then(toml::Value::as_str) {
                        Some(word @ ("advisory" | "warn")) => {
                            return Err(retired_severity(id, word));
                        }
                        Some("error") => {
                            out.severity.insert(id.to_owned(), Severity::Error);
                        }
                        Some("off") => {
                            out.disabled.insert(id.to_owned());
                        }
                        _ => {}
                    }
                    if let Some(toml::Value::Array(items)) = entry.get("gates") {
                        out.gates.insert(id.to_owned(), parse_gates(id, items)?);
                    }
                    if entry.get("disabled").and_then(toml::Value::as_bool) == Some(true) {
                        out.disabled.insert(id.to_owned());
                    }
                }
                _ => {}
            }
        }
        Ok(out)
    }
}

#[allow(
    clippy::disallowed_methods,
    reason = "reads the product's own config file, which is not walked content"
)]
/// The `[rules]` of `<root>/<product>.toml`, or the defaults when it is absent or unreadable.
fn product_settings(root: &std::path::Path, product: &str) -> RuleSettings {
    let path = root.join(format!("{product}.toml"));
    match std::fs::read_to_string(&path) {
        Ok(text) => RuleSettings::from_toml(&text).unwrap_or_else(|e| {
            tracing::warn!(path = %path.display(), error = %e, "[rules] unreadable; defaults used");
            RuleSettings::default()
        }),
        Err(_) => RuleSettings::default(),
    }
}

// frob:ticket 01M5WAN9GG0E1M9PM16B3EMY2Z
/// Drop the findings of every rule switched off by `[rules.<id>] severity = "off"` (or `disabled = true`) in `<root>/<product>.toml`; returns how many were dropped.
pub fn drop_disabled_product_findings(
    root: &std::path::Path,
    product: &str,
    findings: &mut Vec<Finding>,
) -> usize {
    let settings = product_settings(root, product);
    if settings.disabled.is_empty() {
        return 0;
    }
    let before = findings.len();
    findings.retain(|f| !settings.disabled.contains(f.rule.as_str()));
    let dropped = before - findings.len();
    tracing::info!(
        product,
        dropped,
        "findings dropped for rules switched off in [rules]"
    );
    dropped
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-rules/src/settings.rs::shipped_in
    #[test]
    fn shipped_in_matches_the_minor_line_only() {
        assert!(shipped_in("0.532.0", "0.532.3"));
        assert!(shipped_in("0.532.0", "0.532.0-dev"));
        assert!(!shipped_in("0.532.0", "0.533.0"));
        assert!(!shipped_in("0.532.0", "dev"));
    }

    // frob:tests crates/gob-rules/src/settings.rs::from_toml
    #[test]
    fn a_retired_ramp_key_is_accepted_and_ignored() {
        let s = RuleSettings::from_toml("[rules]\nramp = false\n").unwrap();
        assert_eq!(s, RuleSettings::default());
        assert!(RuleSettings::from_toml("[rules]\nramp = 3\n").is_ok());
    }

    // frob:tests crates/gob-rules/src/settings.rs::from_toml
    #[test]
    fn warn_and_advisory_severity_are_config_errors_naming_the_replacement() {
        for word in ["warn", "advisory"] {
            let err = RuleSettings::from_toml(&format!("[rules.AAA001]\nseverity = \"{word}\"\n"))
                .unwrap_err();
            assert!(err.contains("error\" plus a baseline"), "{err}");
            assert!(err.contains("\"off\""), "{err}");
        }
    }

    // frob:tests crates/gob-rules/src/settings.rs::from_toml
    #[test]
    fn gates_are_read_and_bad_words_are_config_errors() {
        let s =
            RuleSettings::from_toml("[rules.AAA001]\ngates = [\"local\", \"release\"]\n").unwrap();
        assert_eq!(s.gates["AAA001"], [Gate::Local, Gate::Release].into());
        assert!(RuleSettings::from_toml("[rules.AAA001]\ngates = [\"prod\"]\n").is_err());
        assert!(RuleSettings::from_toml("[rules.AAA001]\ngates = []\n").is_err());
    }

    // frob:tests crates/gob-rules/src/settings.rs::from_toml
    #[test]
    fn severity_off_disables_and_error_is_accepted() {
        let s = RuleSettings::from_toml(
            "[rules.AAA001]\nseverity = \"off\"\n[rules.BBB001]\nseverity = \"error\"\n",
        )
        .unwrap();
        assert!(s.disabled.contains("AAA001"));
        assert_eq!(s.severity.get("BBB001"), Some(&Severity::Error));
    }

    // frob:tests crates/gob-rules/src/settings.rs::drop_disabled_product_findings
    #[test]
    fn findings_of_rules_switched_off_in_the_product_config_are_dropped() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("prod.toml"),
            "[rules.AAA001]\nseverity = \"off\"\n",
        )
        .unwrap();
        let mk = |id: &str| Finding::new(id.parse().unwrap(), Severity::Error, None, "m", "a");
        let mut findings = vec![mk("AAA001"), mk("BBB001")];
        assert_eq!(
            drop_disabled_product_findings(dir.path(), "prod", &mut findings),
            1
        );
        assert_eq!(findings.len(), 1);
        assert_eq!(findings[0].rule.as_str(), "BBB001");
        assert_eq!(
            drop_disabled_product_findings(dir.path(), "none", &mut findings),
            0
        );
    }
}
