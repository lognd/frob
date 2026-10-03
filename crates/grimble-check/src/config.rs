//! The `grimble.toml` tables owned by grimble: `[compute]`, `[packs]` and `[grimble]`.
//!
//! `[check]` and `[perf]` belong to `gob-check`. The pack tables are accepted and
//! validated here (packs.md 3.6) but no pack is loaded yet; a run that enables one says so.

use std::path::Path;

use gob_config::{ConfigError, ConfigTable};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// Product name, the stem of `grimble.toml` and of the `.grimble/` state directory.
pub const PRODUCT: &str = "grimble";

pub use gob_config::{ComputeTable, blake3_tagged, compute_digest};

/// One `[[packs.external]]` entry (packs.md 3.4): a pack fetched once and vendored.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ExternalPack {
    /// Pack id, `ext/NAME`.
    pub id: String,
    /// `https` URL the pack is fetched from.
    pub url: String,
    /// The pack digest the author expects (`blake3:...`).
    pub digest: String,
}

/// Which data packs the repository enables (packs.md 3.6). Packs are not loaded yet.
#[derive(Debug, Clone, PartialEq, Eq, ConfigTable)]
#[config(table = "packs", materialize)]
pub struct PacksTable {
    /// Enabled pack ids in load order.
    #[config(default = Vec::new(), enforcement)]
    pub enabled: Vec<String>,
    /// Path of the pack lock, relative to the repository root.
    #[config(default = "grimble.packs.lock".to_owned(), enforcement)]
    pub lock: String,
    /// External packs (`[[packs.external]]`).
    #[config(default = Vec::new())]
    pub external: Vec<ExternalPack>,
    /// Repository severity overrides by atom then rule (`[packs.severity]`).
    #[config(default = std::collections::BTreeMap::new())]
    pub severity: std::collections::BTreeMap<String, std::collections::BTreeMap<String, String>>,
}

impl PacksTable {
    /// Load `[packs]` from `<root>/grimble.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        Ok(gob_config::load::<Self>(root, PRODUCT)?.value)
    }

    /// True when the repository asks for packs, which this build does not load.
    pub fn requests_packs(&self) -> bool {
        !self.enabled.is_empty() || !self.external.is_empty()
    }
}

/// The warning printed when packs are requested but not loaded.
pub const PACKS_NOT_LOADED: &str = "packs are enabled in grimble.toml but this build does not load packs yet; PACK rules and pack atoms are not evaluated";

/// The `[grimble]` table: binding policy (binding.md 6).
#[derive(Debug, Clone, PartialEq, Eq, ConfigTable)]
#[config(table = "grimble")]
pub struct GrimbleTable {
    /// Selectors whose public units must have an owner (SYS005); empty turns the rule off.
    #[config(default = Vec::new())]
    pub modeled: Vec<String>,
    /// Warn rules SYS001 and SYS005 become Errors.
    #[config(default = false)]
    pub strict: bool,
}

impl GrimbleTable {
    /// Load `[grimble]` from `<root>/grimble.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        Ok(gob_config::load::<Self>(root, PRODUCT)?.value)
    }
}
