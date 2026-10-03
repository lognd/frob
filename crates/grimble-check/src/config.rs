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

/// The substrate `[compute]` knobs every product reads (architecture.md section 6).
#[derive(Debug, Clone, PartialEq, Eq, ConfigTable)]
#[config(table = "compute", materialize)]
pub struct ComputeTable {
    /// How an unannotated public signature is treated (`warn-unresolved` or `required`).
    #[config(default = "warn-unresolved".to_owned(), enforcement)]
    pub public_signatures: String,
    /// How an undeclared effect is treated.
    #[config(default = "warn-unresolved".to_owned(), enforcement)]
    pub effects: String,
    /// How a dynamic call is treated.
    #[config(default = "warn-unresolved".to_owned(), enforcement)]
    pub dynamic_calls: String,
    /// The macro and template expansion step budget.
    #[config(default = 1000, enforcement)]
    pub expansion_steps: u64,
    /// How an unnormalizable construct is treated.
    #[config(default = "warn-unresolved".to_owned(), enforcement)]
    pub normalization: String,
    /// How a notebook with an undeclared cell order is treated.
    #[config(default = "warn-unresolved".to_owned(), enforcement)]
    pub notebook_order: String,
}

impl ComputeTable {
    /// The canonical JSON of the six knobs: keys sorted bytewise, no whitespace (sibling-contract 3.3).
    pub fn canonical_json(&self) -> String {
        let s = |v: &str| serde_json::Value::String(v.to_owned()).to_string();
        format!(
            "{{\"dynamic_calls\":{},\"effects\":{},\"expansion_steps\":{},\"normalization\":{},\"notebook_order\":{},\"public_signatures\":{}}}",
            s(&self.dynamic_calls),
            s(&self.effects),
            self.expansion_steps,
            s(&self.normalization),
            s(&self.notebook_order),
            s(&self.public_signatures),
        )
    }

    /// `blake3:` plus the hex blake3 of [`Self::canonical_json`].
    ///
    /// This is the one implementation grimble has; `gob-config` is meant to host it
    /// (sibling-contract 10) and the digest does not change when it moves.
    pub fn digest(&self) -> String {
        blake3_tagged(self.canonical_json().as_bytes())
    }

    /// The knobs as the `compute` object of the sibling document.
    pub fn to_value(&self) -> serde_json::Value {
        serde_json::json!({
            "public_signatures": self.public_signatures,
            "effects": self.effects,
            "dynamic_calls": self.dynamic_calls,
            "expansion_steps": self.expansion_steps,
            "normalization": self.normalization,
            "notebook_order": self.notebook_order,
        })
    }

    /// Load `[compute]` from `frob.toml` when it exists, else from `grimble.toml`.
    ///
    /// Returns the table and the product file it came from (sibling-contract 2).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load_for(root: &Path) -> Result<(Self, &'static str), ConfigError> {
        let source = if root.join("frob.toml").is_file() {
            "frob"
        } else {
            PRODUCT
        };
        let table = gob_config::load::<Self>(root, source)?.value;
        tracing::debug!(source, digest = %table.digest(), "compute knobs loaded");
        Ok((table, source))
    }
}

/// `blake3:` plus the lowercase hex blake3 of `bytes`.
pub fn blake3_tagged(bytes: &[u8]) -> String {
    format!("blake3:{}", blake3::hash(bytes).to_hex())
}

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
