//! Base-ref trust for CI (security.md 2.3, I1): trust exactly the (tree digest,
//! effects) pairs recorded in the pack lock read at a protected ref.
//!
//! This module is pure: the caller reads the lock text from git objects at the
//! ref (never the work tree) and hands it to [`BaseRefTrust::from_lock_toml`].
//! A pack the change adds or alters has no matching pair and decides to
//! [`BaseRefVerdict::UntrustedInChange`]: it runs with no effects. No user
//! store is read or written.

// frob:ticket 01M3ZX7V587K71E94E0AE4GWW8

use std::collections::BTreeMap;

use tracing::{debug, info, warn};

/// Effects by family, as recorded in the lock.
pub type Effects = BTreeMap<String, Vec<String>>;

/// Why a base-ref lock could not be used.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum BaseRefError {
    /// The lock text is not valid TOML or lacks the expected shape.
    #[error("E-TRUST-BASEREF-LOCK: base-ref pack lock is malformed: {0}")]
    Malformed(String),
}

/// What base-ref trust decides for one live pack.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BaseRefVerdict {
    /// The pack is unchanged since the ref; it runs with the effects recorded there.
    Trusted {
        /// The effects recorded in the lock at the ref.
        effects: Effects,
    },
    /// The pack is new or changed by the change under test: no effects, no privileges.
    UntrustedInChange,
}

impl BaseRefVerdict {
    /// Whether the pack is trusted.
    #[must_use]
    pub fn is_trusted(&self) -> bool {
        matches!(self, Self::Trusted { .. })
    }
}

/// The (name, tree digest, effects) triples present in the lock at a ref.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct BaseRefTrust {
    packs: Vec<(String, String, Effects)>,
}

impl BaseRefTrust {
    /// Trust nothing: the ref has no lock, so every pack is untrusted-in-change.
    #[must_use]
    pub fn empty() -> Self {
        Self::default()
    }

    /// Parses the pack lock text read at the ref.
    ///
    /// # Errors
    /// [`BaseRefError::Malformed`] when the text is not a lock-shaped TOML document.
    pub fn from_lock_toml(text: &str) -> Result<Self, BaseRefError> {
        let bad = |why: String| {
            warn!(%why, "base-ref pack lock refused");
            BaseRefError::Malformed(why)
        };
        let table: toml::Table = text
            .parse()
            .map_err(|e: toml::de::Error| bad(e.to_string()))?;
        let mut packs = Vec::new();
        let entries = match table.get("pack") {
            None => &[][..],
            Some(v) => v
                .as_array()
                .ok_or_else(|| bad("`pack` is not an array".to_owned()))?
                .as_slice(),
        };
        for entry in entries {
            let field = |k: &str| entry.get(k).and_then(toml::Value::as_str);
            let (Some(name), Some(tree)) = (field("name"), field("tree")) else {
                return Err(bad("a pack lacks `name` or `tree`".to_owned()));
            };
            let mut effects = Effects::new();
            if let Some(t) = entry.get("effects").and_then(toml::Value::as_table) {
                for (family, items) in t {
                    let list = items
                        .as_array()
                        .ok_or_else(|| bad(format!("effects.{family} is not an array")))?
                        .iter()
                        .filter_map(|i| i.as_str().map(str::to_owned))
                        .collect();
                    effects.insert(family.clone(), list);
                }
            }
            packs.push((name.to_owned(), tree.to_owned(), effects));
        }
        info!(packs = packs.len(), "base-ref trust loaded");
        Ok(Self { packs })
    }

    /// Decides the live pack `name` with tree digest `tree`.
    #[must_use]
    pub fn decide(&self, name: &str, tree: &str) -> BaseRefVerdict {
        if let Some((_, _, effects)) = self.packs.iter().find(|(n, t, _)| n == name && t == tree) {
            debug!(pack = name, "pack unchanged since base ref; trusted");
            return BaseRefVerdict::Trusted {
                effects: effects.clone(),
            };
        }
        warn!(
            pack = name,
            "pack new or changed since base ref; untrusted-in-change"
        );
        BaseRefVerdict::UntrustedInChange
    }
}
