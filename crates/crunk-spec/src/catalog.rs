//! The rule catalog rows, severities and the other design constants the spec owns.
//!
//! The spec depends on nothing downstream, so the catalog lives here as `(prefix, number,
//! default severity)` rows; the rules crate reads it instead of keeping a drifting copy.

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

use std::fmt;

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// A rule's enforcement level: `error` fails the run, `warn` reports, `off` is silent.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum Severity {
    /// Fails the run.
    Error,
    /// Reported, does not fail the run.
    Warn,
    /// Silent.
    Off,
}

impl Severity {
    /// Parse `error`, `warn` or `off`.
    pub fn parse(text: &str) -> Option<Self> {
        match text {
            "error" => Some(Self::Error),
            "warn" => Some(Self::Warn),
            "off" => Some(Self::Off),
            _ => None,
        }
    }

    /// The lowercase spelling used in `crunk.toml`.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Error => "error",
            Self::Warn => "warn",
            Self::Off => "off",
        }
    }
}

impl fmt::Display for Severity {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// One catalog row: rule family prefix, number and default severity.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CatalogRow {
    /// Family prefix, e.g. `COLOR`.
    pub prefix: &'static str,
    /// Number within the family, e.g. `1` for `COLOR001`.
    pub number: u32,
    /// Severity when `[lint]` does not override it.
    pub default: Severity,
}

impl CatalogRow {
    /// The rule id, e.g. `COLOR001`.
    pub fn id(&self) -> String {
        format!("{}{:03}", self.prefix, self.number)
    }
}

const fn row(prefix: &'static str, number: u32, default: Severity) -> CatalogRow {
    CatalogRow {
        prefix,
        number,
        default,
    }
}

/// Every rule the Python catalog declares, in catalog order.
///
/// Gallery defaults follow the owner decision of 2026-09-26: missing render, unapproved,
/// expired and rejected default to error; a discovered-but-undeclared screen to warn.
pub const CATALOG: &[CatalogRow] = &[
    row("COLOR", 1, Severity::Error),
    row("COLOR", 2, Severity::Error),
    row("SPACE", 1, Severity::Error),
    row("TYPE", 1, Severity::Error),
    row("TYPE", 2, Severity::Error),
    row("TYPE", 3, Severity::Warn),
    row("RADIUS", 1, Severity::Warn),
    row("LAYER", 1, Severity::Error),
    row("CONTRAST", 1, Severity::Error),
    row("ORG", 1, Severity::Error),
    row("ORG", 2, Severity::Error),
    row("ORG", 3, Severity::Error),
    row("ORG", 4, Severity::Error),
    row("ORG", 5, Severity::Error),
    row("TW", 1, Severity::Error),
    row("TW", 2, Severity::Error),
    row("TW", 3, Severity::Warn),
    row("TW", 4, Severity::Error),
    row("TW", 5, Severity::Error),
    row("TOKENS", 1, Severity::Error),
    row("WAIVE", 1, Severity::Error),
    row("SIZE", 1, Severity::Warn),
    row("BP", 1, Severity::Error),
    row("BP", 2, Severity::Error),
    row("BP", 3, Severity::Error),
    row("GALLERY", 1, Severity::Error),
    row("GALLERY", 2, Severity::Error),
    row("GALLERY", 3, Severity::Error),
    row("GALLERY", 4, Severity::Error),
    row("GALLERY", 5, Severity::Warn),
];

/// The WCAG AA contrast floor CONTRAST001 and the contrast report share.
pub const CONTRAST_AA_FLOOR: f64 = 4.5;

/// The Tailwind v3 default breakpoints, applied when `[breakpoints]` is absent but a
/// `[tailwind]` config is declared.
pub const TAILWIND_V3_BREAKPOINTS: &[(&str, i64)] = &[
    ("sm", 640),
    ("md", 768),
    ("lg", 1024),
    ("xl", 1280),
    ("2xl", 1536),
];

/// The default `base_required` utility families (BP002), applied whenever `[breakpoints]`
/// resolves to non-empty without an explicit `base_required`.
pub const DEFAULT_BASE_REQUIRED: &[&str] = &[
    "flex", "grid", "block", "hidden", "w-", "h-", "col-", "row-",
];

/// Renderer ids a `[[platform]]` may name (the gallery's built-in registry).
pub const RENDERER_IDS: &[&str] = &["command", "web"];

/// Browser engines the built-in `web` renderer drives.
pub const ENGINE_IDS: &[&str] = &["chromium", "firefox", "webkit"];

/// The `prefers-color-scheme` values a platform's media features may emulate.
pub const COLOR_SCHEMES: &[&str] = &["dark", "light", "no-preference"];

/// True when `id` is a catalog rule id such as `COLOR001`.
pub fn is_rule_id(id: &str) -> bool {
    CATALOG.iter().any(|r| r.id() == id)
}

/// Every catalog rule id, in catalog order.
pub fn rule_ids() -> Vec<String> {
    CATALOG.iter().map(CatalogRow::id).collect()
}

/// The catalog default severity of `id`, if it is a catalog rule.
pub fn default_severity(id: &str) -> Option<Severity> {
    CATALOG.iter().find(|r| r.id() == id).map(|r| r.default)
}
