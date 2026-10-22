//! The `[invariants]` and `[coverage]` config tables: forbidden imports (INV002) and coverage minimums (COV004).

use std::path::Path;

use gob_config::{ConfigError, ConfigTable};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// The product whose `frob.toml` carries the table.
const PRODUCT: &str = "frob";

/// One forbidden import edge: files matching `from` must not import `to`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ForbidImport {
    /// A crate directory name (no `/` or glob characters) or a path glob over importing files.
    pub from: String,
    /// A crate or module prefix (`gob_rules`, `crate::cache`); `-` and `_` are equivalent.
    pub to: String,
    /// Why the import is forbidden (shown in the finding).
    pub reason: String,
}

/// Architecture invariants enforced over the import graph (INV002).
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "invariants")]
pub struct InvariantsConfig {
    /// Imports no file matching `from` may contain; each entry needs a `reason`.
    #[config(default = Vec::new())]
    pub forbid_imports: Vec<ForbidImport>,
}

impl InvariantsConfig {
    /// Load `[invariants]` from `<root>/frob.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        Ok(gob_config::load::<Self>(root, PRODUCT)?.value)
    }
}

// frob:ticket 01M4FD1NX760N78Z1T60MQ76H2
/// One coverage minimum: the files matching `scope` must reach `line` and `branch` percent.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct CoverageThreshold {
    /// A path glob over the covered files, or a directory prefix (no glob characters).
    pub scope: String,
    /// Minimum line coverage in percent (0 to 100); omit to leave lines unchecked.
    #[serde(default)]
    pub line: Option<f64>,
    /// Minimum branch coverage in percent (0 to 100); omit to leave branches unchecked.
    #[serde(default)]
    pub branch: Option<f64>,
}

// frob:ticket 01M4FD1NX760N78Z1T60MQ76H2
/// Coverage minimums per scope, measured from an lcov report (COV004).
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "coverage")]
pub struct CoverageConfig {
    /// The lcov report to read, relative to the repository root.
    #[config(default = "lcov.info".to_owned())]
    pub report: String,
    /// Minimums per scope, written as `[[coverage.threshold]]` entries.
    #[config(default = Vec::new())]
    pub threshold: Vec<CoverageThreshold>,
}

impl CoverageConfig {
    /// Load `[coverage]` from `<root>/frob.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        Ok(gob_config::load::<Self>(root, PRODUCT)?.value)
    }
}
