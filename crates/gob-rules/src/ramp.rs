//! Ramp-in (inert): Warn is retired, so no rule is capped; ~MBFZHZD removes this module.
//!
//! The window is the minor line of `since` (`0.532.0` ramps through `0.532.x`); the release that
//! ends it is the next minor, `0.533.0`. Pre-release suffixes (`-dev`) are ignored, so a dev build
//! of the next release is already past the window.

// frob:ticket 01M4HDXVZNXTNANMHRGVGQ66DC
use crate::decl::RuleDef;
use crate::finding::Finding;
use crate::meta::Severity;
use crate::registry::{Registry, RuleSettings};

/// A parsed `major.minor.patch` triple; a pre-release or build suffix is dropped.
fn triple(text: &str) -> Option<(u64, u64, u64)> {
    let core = text.split(['-', '+']).next()?;
    let mut parts = core.split('.').map(str::parse::<u64>);
    let major = parts.next()?.ok()?;
    let minor = parts.next()?.ok()?;
    let patch = parts.next()?.ok()?;
    parts.next().is_none().then_some((major, minor, patch))
}

/// The release at which a rule first shipped in `since` stops being ramped (`0.532.0` gives `0.533.0`); `None` when `since` is not a version.
#[must_use]
pub fn ramp_end(since: &str) -> Option<String> {
    let (major, minor, _) = triple(since)?;
    Some(format!("{major}.{}.0", minor + 1))
}

/// True when `current` is inside the ramp window of a rule or atom first shipped in `since`; false when either is not a version.
#[must_use]
pub fn in_ramp(since: &str, current: &str) -> bool {
    let (Some(first), Some(now)) = (triple(since), triple(current)) else {
        return false;
    };
    now >= first && (now.0, now.1) == (first.0, first.1)
}

/// The severity a rule or atom runs at during its ramp, plus the note naming when it takes its declared severity.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Ramped {
    /// Severity to report at.
    pub severity: Severity,
    /// Note naming the release where the declared severity takes effect.
    pub note: String,
}

/// Ramp-in is inert: Warn no longer exists (rules.md 6.1.1), so no severity is ever capped; ~MBFZHZD removes this plumbing.
#[must_use]
pub fn ramp(since: &str, declared: Severity, current: &str) -> Option<Ramped> {
    tracing::trace!(since, ?declared, current, "ramp-in is inert");
    None
}

/// The config error for a retired `severity` spelling, naming its replacement.
fn retired_severity(id: &str, word: &str) -> String {
    format!(
        "[rules.{id}] severity = \"{word}\" is no longer supported: use \"error\" plus a baseline in frob-baseline.toml, or \"off\""
    )
}

impl RuleSettings {
    /// Read `[rules] ramp`, the `[rules.<id>] severity` (`error` or `off`) ids and `disabled = true` ids from the `text` of a product config; a missing `[rules]` gives the defaults.
    ///
    /// # Errors
    ///
    /// The TOML parse error when `text` is not TOML or `[rules] ramp` is not a boolean, or the message naming `error` plus a baseline, or `off`, when a severity is `warn` or `advisory`.
    pub fn from_toml(text: &str) -> Result<Self, String> {
        let doc: toml::Table = text.parse().map_err(|e: toml::de::Error| e.to_string())?;
        let mut out = Self::default();
        let Some(toml::Value::Table(rules)) = doc.get("rules") else {
            return Ok(out);
        };
        for (key, value) in rules {
            match (key.as_str(), value) {
                ("ramp", toml::Value::Boolean(on)) => out.ramp = *on,
                ("ramp", _) => return Err("`[rules] ramp` must be true or false".to_owned()),
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
                    if entry.get("disabled").and_then(toml::Value::as_bool) == Some(true) {
                        out.disabled.insert(id.to_owned());
                    }
                }
                _ => {}
            }
        }
        Ok(out)
    }

    /// Cap every Error finding of a rule new in release `current` (its `since` from `since_of`) at Warn, noting the release it becomes Error; returns how many were ramped.
    ///
    /// Nothing is ramped when `[rules] ramp = false` or the rule carries an explicit `[rules.<id>] severity`.
    pub fn ramp_findings(
        &self,
        findings: &mut [Finding],
        since_of: &dyn Fn(&str) -> Option<&'static str>,
        current: &str,
    ) -> usize {
        if !self.ramp {
            return 0;
        }
        let mut ramped = 0;
        for f in findings
            .iter_mut()
            .filter(|f| f.severity == Severity::Error)
        {
            let id = f.rule.as_str();
            if self.severity.contains_key(id) {
                continue;
            }
            let Some(since) = since_of(id) else { continue };
            if let Some(r) = ramp(since, Severity::Error, current) {
                tracing::info!(rule = id, "finding ramped from error to warn");
                f.severity = r.severity;
                f.message = format!("{} ({})", f.message, r.note);
                ramped += 1;
            }
        }
        ramped
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

// frob:ticket 01M5WAN9GG0E1M9PM16B3EMY2Z
/// Ramp the Error findings of rules new in release `current` using the `[rules]` of `<root>/<product>.toml` (defaults when absent or unreadable); a rule's `since` comes from `defs` first, then `registry`. Returns how many were ramped.
pub fn ramp_product_findings(
    root: &std::path::Path,
    product: &str,
    registry: &Registry,
    defs: &[&'static RuleDef],
    findings: &mut [Finding],
    current: &str,
) -> usize {
    let settings = product_settings(root, product);
    let since_of = |id: &str| {
        defs.iter()
            .find(|d| d.id == id)
            .map(|d| d.since)
            .or_else(|| registry.by_id(id).map(|m| m.since))
    };
    settings.ramp_findings(findings, &since_of, current)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-rules/src/ramp.rs::ramp
    #[test]
    fn ramp_is_inert_for_every_input() {
        assert!(ramp("0.532.0", Severity::Error, "0.532.0").is_none());
        assert!(ramp("0.532.0", Severity::Error, "dev").is_none());
        assert!(in_ramp("0.532.0", "0.532.3"));
        assert_eq!(ramp_end("1.2.3").as_deref(), Some("1.3.0"));
        assert_eq!(ramp_end("1.2"), None);
    }

    // frob:tests crates/gob-rules/src/ramp.rs::from_toml
    #[test]
    fn warn_and_advisory_severity_are_config_errors_naming_the_replacement() {
        for word in ["warn", "advisory"] {
            let err = RuleSettings::from_toml(&format!("[rules.AAA001]\nseverity = \"{word}\"\n"))
                .unwrap_err();
            assert!(err.contains("error\" plus a baseline"), "{err}");
            assert!(err.contains("\"off\""), "{err}");
        }
    }

    // frob:tests crates/gob-rules/src/ramp.rs::from_toml
    #[test]
    fn severity_off_disables_and_error_is_accepted() {
        let s = RuleSettings::from_toml(
            "[rules.AAA001]\nseverity = \"off\"\n[rules.BBB001]\nseverity = \"error\"\n",
        )
        .unwrap();
        assert!(s.disabled.contains("AAA001"));
        assert_eq!(s.severity.get("BBB001"), Some(&Severity::Error));
    }

    // frob:tests crates/gob-rules/src/ramp.rs::drop_disabled_product_findings
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
