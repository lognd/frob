//! The `[invariants]` config table: forbidden imports checked by INV002.

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
