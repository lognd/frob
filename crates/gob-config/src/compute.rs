//! The substrate `[compute]` table and its canonical digest (sibling-contract 3.3).
//!
//! Every product reads these six knobs from its own config file (frob and grimble
//! share them in `frob.toml`). The digest of the resolved table is how frob checks
//! that a sibling analysed the repository under the same compute settings.

use std::path::Path;

use crate::{ConfigError, ConfigTable};

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
    #[must_use]
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

    /// The knobs as the `compute` object of the sibling document.
    #[must_use]
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

    /// [`compute_digest`] of this table.
    #[must_use]
    pub fn digest(&self) -> String {
        compute_digest(self)
    }

    /// [`Self::load_for_product`] for `grimble`, the one product that reads `[compute]` today.
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load_for(root: &Path) -> Result<(Self, &'static str), ConfigError> {
        Self::load_for_product(root, "grimble")
    }

    /// Load `[compute]` from `frob.toml` when it exists, else from `<product>.toml`.
    ///
    /// Returns the table and the config stem it came from (sibling-contract 2).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load_for_product<'a>(
        root: &Path,
        product: &'a str,
    ) -> Result<(Self, &'a str), ConfigError> {
        let source = if root.join("frob.toml").is_file() {
            "frob"
        } else {
            product
        };
        let table = crate::load::<Self>(root, source)?.value;
        tracing::debug!(source, digest = %compute_digest(&table), "compute knobs loaded");
        Ok((table, source))
    }
}

/// The canonical compute digest: `blake3:` plus the hex blake3 of the canonical JSON.
///
/// The single implementation frob and grimble share; a sibling document carries it
/// as `compute_digest` and frob refuses a document whose digest differs from its own.
#[must_use]
pub fn compute_digest(table: &ComputeTable) -> String {
    blake3_tagged(table.canonical_json().as_bytes())
}

/// `blake3:` plus the lowercase hex blake3 of `bytes`.
#[must_use]
pub fn blake3_tagged(bytes: &[u8]) -> String {
    format!("blake3:{}", blake3::hash(bytes).to_hex())
}
