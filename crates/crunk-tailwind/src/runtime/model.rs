//! Typed results of the Tailwind runtime: compiled utilities per candidate and the resolved theme.

// frob:ticket 01M43ARYX61ESX3S9XG1WS0DQ4

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

/// The finding reason code for every result the runtime could not compute.
pub const UNRESOLVED_CODE: &str = "unresolved-by-tailwind";

/// The Tailwind major version of the project's own install.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum TailwindVersion {
    /// Tailwind 3 (JS config).
    V3,
    /// Tailwind 4 (CSS-first, optionally bridging a JS config with `@config`).
    V4,
}

impl TailwindVersion {
    /// The major number.
    pub fn major(self) -> u64 {
        match self {
            Self::V3 => 3,
            Self::V4 => 4,
        }
    }
}

/// One at-rule a declaration is nested in.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AtRuleWrap {
    /// The at-rule name without `@` (`media`, `layer`, `supports`).
    pub name: String,
    /// Its prelude text.
    pub params: String,
}

/// One declaration Tailwind emitted for a class.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClassDeclaration {
    /// The lowercase property name.
    pub property: String,
    /// The value text.
    pub value: String,
    /// The selector as Tailwind wrote it (escapes and pseudo-classes included).
    pub selector: String,
    /// The at-rules it sits inside, outermost first.
    pub at_rules: Vec<AtRuleWrap>,
}

/// Whether a candidate compiled to CSS.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ClassStatus {
    /// Tailwind emitted CSS for it.
    Valid,
    /// Tailwind ran and emitted nothing: not a Tailwind class.
    Invalid,
    /// Tailwind was not run; the answer is unknown.
    Unresolved,
}

/// One candidate's outcome.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClassResult {
    /// The candidate as given.
    pub candidate: String,
    /// Valid, invalid or unresolved.
    pub status: ClassStatus,
    /// The declarations when valid; empty otherwise.
    pub declarations: Vec<ClassDeclaration>,
}

/// The compiled utilities of a candidate set.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RunResult {
    /// The version the truth was computed against.
    pub version: TailwindVersion,
    /// The config or CSS entry the helper reported, if any.
    pub config_path: Option<String>,
    /// One result per requested candidate, in request order.
    pub results: Vec<ClassResult>,
}

/// The project's own contribution to Tailwind's merged theme, as a flat `{name: value}` map.
///
/// v3 keys are the last segment of each differing dotted path; v4 keys are the raw `--name`
/// custom properties (the ingest layer strips namespaces).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ThemeResult {
    /// The version the theme was resolved against.
    pub version: TailwindVersion,
    /// The config or CSS entry the helper reported, if any.
    pub config_path: Option<String>,
    /// The project-owned entries, sorted by key.
    pub theme: BTreeMap<String, String>,
}

/// Why the runtime did not run Tailwind. Never a clean result: a rule that needs the runtime
/// reports Unresolved with [`UNRESOLVED_CODE`] and this reason.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error, Serialize, Deserialize)]
#[non_exhaustive]
pub enum Unresolved {
    /// Static mode was requested (`--static`, `[tailwind] engine = "static"`).
    #[error("static mode requested; Tailwind was not run")]
    StaticMode,
    /// No `node` binary is on `PATH`.
    #[error(
        "no `{binary}` binary found on PATH; Tailwind was not run (install node or use static mode)"
    )]
    NodeMissing {
        /// The binary name looked up.
        binary: String,
    },
    /// The project has no `node_modules/tailwindcss` (here or in an ancestor).
    #[error("no tailwindcss install found in node_modules from {project_root} upward")]
    TailwindMissing {
        /// Where the search started.
        project_root: String,
    },
    /// The installed `tailwindcss/package.json` could not be read as a version.
    #[error("the installed tailwindcss version is unreadable: {detail}")]
    VersionUnreadable {
        /// Why.
        detail: String,
    },
    /// The installed major version has no runner.
    #[error("tailwindcss major version {major} is not supported (3 and 4 are)")]
    UnsupportedVersion {
        /// The major found, when it parsed.
        major: String,
    },
    /// Tailwind 4 needs the CSS entry file, and none was given or detected.
    #[error("tailwindcss 4 needs the CSS entry file (`[tailwind] css_entry`); none was given")]
    MissingCssEntry,
}

impl Unresolved {
    /// The finding reason code ([`UNRESOLVED_CODE`]).
    pub fn code(&self) -> &'static str {
        UNRESOLVED_CODE
    }

    /// An all-[`ClassStatus::Unresolved`] result list for `candidates`.
    pub fn class_results(&self, candidates: &[String]) -> Vec<ClassResult> {
        candidates
            .iter()
            .map(|c| ClassResult {
                candidate: c.clone(),
                status: ClassStatus::Unresolved,
                declarations: Vec::new(),
            })
            .collect()
    }
}

/// Either Tailwind's answer or the reason there is none.
#[derive(Debug, Clone, PartialEq, Eq)]
#[must_use]
pub enum Evaluation<T> {
    /// The helper ran and answered.
    Resolved(T),
    /// The helper did not run; see the reason.
    Unresolved(Unresolved),
}

impl<T> Evaluation<T> {
    /// The answer, or the reason it is missing.
    ///
    /// # Errors
    ///
    /// The [`Unresolved`] reason when Tailwind was not run.
    pub fn resolved(self) -> Result<T, Unresolved> {
        match self {
            Self::Resolved(t) => Ok(t),
            Self::Unresolved(u) => Err(u),
        }
    }
}
