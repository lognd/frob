//! The `grimble.toml` tables owned by grimble: `[compute]`, `[packs]` and `[grimble]`.
//!
//! `[check]` and `[perf]` belong to `gob-check`. The pack tables are accepted and
//! validated here (packs.md 3.6); repository packs load atoms only (see `packs`), and a run that enables anything else says so.

// frob:ticket 01M41H9Y7TTWDN6DAQ5C06R6B7
// frob:ticket 01M4FGXVQTN5NJ0JBGWAMVHK82

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

    /// True when the repository asks for packs this build does not load: external packs and
    /// enabled ids outside the `grimble/` built-ins and the `local/` repository packs.
    pub fn requests_packs(&self) -> bool {
        !self.external.is_empty()
            || self
                .enabled
                .iter()
                .any(|id| !id.starts_with("grimble/") && !id.starts_with("local/"))
    }
}

/// The warning printed when packs are requested but not loaded.
pub const PACKS_NOT_LOADED: &str = "packs are enabled in grimble.toml but this build loads only local/ packs (atoms) and built-ins; external packs, the lock and PACK rules are not evaluated";

/// The conventional model root `grimble init` seeds and the `models` knob defaults to.
pub const DEFAULT_MODEL_ROOT: &str = "design/model.grmb";

/// The `[grimble]` table: model roots and binding policy (grmb-spec 3, binding.md 6).
#[derive(Debug, Clone, PartialEq, Eq, ConfigTable)]
#[config(table = "grimble", materialize)]
pub struct GrimbleTable {
    /// Root `.grmb` files, one independent model each; only files reachable from them through
    /// `include` are loaded (MDL019 names the rest, MDL021 fires when none is declared).
    #[config(default = vec![DEFAULT_MODEL_ROOT.to_owned()], enforcement)]
    pub models: Vec<String>,
    /// Selectors whose public units must have an owner (SYS005); empty turns the rule off.
    #[config(default = Vec::new())]
    pub modeled: Vec<String>,
    /// Warn rules SYS001 and SYS005 become Errors.
    #[config(default = false)]
    pub strict: bool,
    /// A Body with fewer tokens than this cannot be paired as a rename (binding.md 5.4 item 3).
    #[config(default = 12_u64)]
    pub rename_min_tokens: u64,
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

/// The ledger directory of `frob.toml` (`[tickets] dir`), the one frob-owned path that is configurable.
///
/// Read straight from the shared file (grimble links no frob crate); a missing or unreadable
/// file, table or key, or a non-string value, gives [`grimble_bind::frob_owned::DEFAULT_LEDGER_DIR`].
pub fn ledger_dir(root: &Path) -> String {
    gob_walk::ledger_dir(root)
}
