//! Ramp-in: a rule first shipped in release N runs at Warn through N, then at its declared severity.
//!
//! The window is the minor line of `since` (`0.532.0` ramps through `0.532.x`); the release that
//! ends it is the next minor, `0.533.0`. Pre-release suffixes (`-dev`) are ignored, so a dev build
//! of the next release is already past the window.

// frob:ticket 01M4HDXVZNXTNANMHRGVGQ66DC
use crate::meta::Severity;

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

/// Cap `declared` at Warn when `current` is inside the ramp window of `since`; `None` when no ramp applies (outside the window, `declared` already at most Warn, or an unparseable version).
#[must_use]
pub fn ramp(since: &str, declared: Severity, current: &str) -> Option<Ramped> {
    if declared <= Severity::Warn || !in_ramp(since, current) {
        return None;
    }
    let end = ramp_end(since)?;
    tracing::debug!(since, current, "rule ramped from error to warn");
    Some(Ramped {
        severity: Severity::Warn,
        note: format!("new in {since}; reported as warn until {end}, when it becomes error"),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-rules/src/ramp.rs::ramp
    #[test]
    fn an_error_rule_is_warn_through_its_release_line_then_error() {
        let r = ramp("0.532.0", Severity::Error, "0.532.0").unwrap();
        assert_eq!(r.severity, Severity::Warn);
        assert!(r.note.contains("0.533.0"), "{}", r.note);
        assert!(ramp("0.532.0", Severity::Error, "0.532.3").is_some());
        assert!(ramp("0.532.0", Severity::Error, "0.533.0").is_none());
        assert!(ramp("0.532.0", Severity::Error, "0.533.0-dev").is_none());
        assert!(ramp("0.532.0", Severity::Error, "0.531.9").is_none());
        assert!(ramp("0.532.0", Severity::Error, "1.0.0").is_none());
    }

    // frob:tests crates/gob-rules/src/ramp.rs::ramp
    #[test]
    fn lower_severities_and_bad_versions_are_never_ramped() {
        assert!(ramp("0.532.0", Severity::Warn, "0.532.0").is_none());
        assert!(ramp("0.532.0", Severity::Advisory, "0.532.0").is_none());
        assert!(ramp("0.532.0", Severity::Error, "dev").is_none());
        assert!(ramp("x", Severity::Error, "0.532.0").is_none());
        assert_eq!(ramp_end("1.2.3").as_deref(), Some("1.3.0"));
        assert_eq!(ramp_end("1.2"), None);
    }
}
