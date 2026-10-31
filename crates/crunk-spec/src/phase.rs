//! The project phase (`phase = "discovery | alpha | beta | live"`, design `crunk.md` section 8).
//!
//! The phase is opt-in and selects a lint profile in `crunk-rules`. This module owns only the
//! value: parsing with a located schema error that lists the four values, and the default that
//! applies (and is reported) when the key is absent.

// frob:ticket 01M5XCYCP797Z6M8WPBW7FAD5W

use std::fmt;
use std::path::Path;

use toml_edit::Document;

use crate::error::SpecError;
use crate::load::location;

/// The GOV.UK service phase a project is in; each ends in an assessment.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Phase {
    /// Exploring the problem; structure only.
    Discovery,
    /// A first build; structure lints only.
    Alpha,
    /// A tested build; the full accessibility set and the human review lock.
    Beta,
    /// In production; metrics and experiments are checked as well.
    Live,
}

/// The phase assumed when `crunk.toml` declares none.
pub const DEFAULT_PHASE: Phase = Phase::Beta;

impl Phase {
    /// The four phases in order, earliest first.
    pub const ALL: [Self; 4] = [Self::Discovery, Self::Alpha, Self::Beta, Self::Live];

    /// The lowercase spelling used in `crunk.toml`.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Discovery => "discovery",
            Self::Alpha => "alpha",
            Self::Beta => "beta",
            Self::Live => "live",
        }
    }

    /// Parse one of the four phase names; `None` for anything else.
    pub fn parse(text: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|p| p.as_str() == text)
    }

    /// The four values joined for an error message, e.g. `discovery, alpha, beta, live`.
    pub fn expected() -> String {
        Self::ALL.map(Self::as_str).join(", ")
    }
}

impl fmt::Display for Phase {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// The phase a project runs under and whether it was declared or defaulted.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ResolvedPhase {
    /// The effective phase.
    pub phase: Phase,
    /// True when `crunk.toml` declares no phase and [`DEFAULT_PHASE`] applies.
    pub defaulted: bool,
}

impl ResolvedPhase {
    /// One line for the check envelope, saying so when the phase was defaulted.
    pub fn note(&self) -> String {
        if self.defaulted {
            format!(
                "phase not set in crunk.toml; defaulting to {} (set phase = one of {})",
                self.phase,
                Phase::expected()
            )
        } else {
            format!("phase = {}", self.phase)
        }
    }
}

/// Read the top-level `phase` key of `text` (the `crunk.toml` at `source`).
///
/// Absent resolves to [`DEFAULT_PHASE`] with `defaulted` set.
///
/// # Errors
///
/// [`SpecError::Malformed`] when `text` is not TOML; a located [`SpecError::Invalid`] listing the
/// four values when `phase` is unknown or not a string.
pub fn read_phase(text: &str, source: &Path) -> Result<ResolvedPhase, SpecError> {
    let doc = match Document::parse(text) {
        Ok(doc) => doc,
        Err(e) => {
            return Err(SpecError::Malformed {
                path: source.to_owned(),
                at: e.span().map(|s| location(text, s.start)),
                message: e.message().to_owned(),
            });
        }
    };
    let Some((key, item)) = doc.as_table().get_key_value("phase") else {
        tracing::info!(default = %DEFAULT_PHASE, "crunk.toml declares no phase; using the default");
        return Ok(ResolvedPhase {
            phase: DEFAULT_PHASE,
            defaulted: true,
        });
    };
    let offset = item.span().or_else(|| key.span()).map(|s| s.start);
    let at = offset.map(|o| location(text, o));
    if let Some(phase) = item.as_str().and_then(Phase::parse) {
        tracing::info!(%phase, "project phase declared");
        Ok(ResolvedPhase {
            phase,
            defaulted: false,
        })
    } else {
        tracing::warn!("crunk.toml phase is not one of the four phases");
        Err(SpecError::Invalid {
            path: source.to_owned(),
            at,
            detail: format!("phase: must be one of {}", Phase::expected()),
            key: Some("phase".to_owned()),
            suggestion: None,
        })
    }
}
