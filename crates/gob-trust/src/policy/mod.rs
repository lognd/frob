//! Effective policy snapshot at a ref and the delta between two of them
//! (security.md 2.7, the inputs of GATE001 and `config diff --base REF`).
//!
//! A [`PolicySnapshot`] is the flattened, canonical form of every setting a
//! gate verdict depends on: packs and their paths, severities, disabled
//! rules, `fail_on*`, `[compute]`, excludes, grants, `replaces`, trust
//! settings, repository-adapter `NotApplicable` claims and in-source
//! declarations. Settings outside those families are ignored, so unrelated
//! edits never show up as policy changes.

use std::collections::BTreeMap;

use tracing::{debug, trace};

/// Top-level config tables whose content is policy (everything else is ignored).
pub const POLICY_ROOTS: &[&str] = &[
    "packs", "rules", "severity", "disable", "compute", "exclude", "excludes", "grants",
    "replaces", "trust", "adapters",
];

/// Prefix of the top-level keys that are policy by name (`fail_on`, `fail_on_*`).
pub const FAIL_ON_PREFIX: &str = "fail_on";

/// Why a policy snapshot could not be built.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum PolicyError {
    /// The config text at the ref is not valid TOML.
    #[error("config at the ref is not valid TOML: {0}")]
    Toml(String),
}

/// One policy setting that differs between base and head.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PolicyChange {
    /// Dotted key of the setting, for example `rules.SEC001.severity`.
    pub key: String,
    /// Canonical value at base, or `None` when the setting did not exist.
    pub old: Option<String>,
    /// Canonical value at head, or `None` when the setting was removed.
    pub new: Option<String>,
}

/// The ordered set of changes between two snapshots; empty when policy is identical.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct PolicyDelta {
    /// Changes sorted by key.
    pub changes: Vec<PolicyChange>,
}

impl PolicyDelta {
    /// True when base and head have identical effective policy.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.changes.is_empty()
    }
}

/// Canonical, flattened effective policy: dotted key to canonical value text.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct PolicySnapshot {
    entries: BTreeMap<String, String>,
}

fn is_policy_root(key: &str) -> bool {
    POLICY_ROOTS.contains(&key) || key.starts_with(FAIL_ON_PREFIX)
}

fn flatten(prefix: &str, value: &toml::Value, out: &mut BTreeMap<String, String>) {
    match value {
        toml::Value::Table(t) if !t.is_empty() => {
            for (k, v) in t {
                flatten(&format!("{prefix}.{k}"), v, out);
            }
        }
        other => {
            trace!(key = prefix, "policy entry");
            out.insert(prefix.to_owned(), other.to_string());
        }
    }
}

impl PolicySnapshot {
    /// Build a snapshot from the config TOML read at one ref.
    ///
    /// # Errors
    /// [`PolicyError::Toml`] when `text` does not parse.
    pub fn from_toml(text: &str) -> Result<Self, PolicyError> {
        let doc: toml::Table = text
            .parse()
            .map_err(|e: toml::de::Error| PolicyError::Toml(e.to_string()))?;
        let mut entries = BTreeMap::new();
        for (k, v) in &doc {
            if is_policy_root(k) {
                flatten(k, v, &mut entries);
            }
        }
        debug!(entries = entries.len(), "policy snapshot built");
        Ok(Self { entries })
    }

    /// Record an adapter `NotApplicable` claim or in-source declaration a P+ verdict depends on.
    #[must_use]
    pub fn with_declaration(mut self, key: &str, value: &str) -> Self {
        debug!(key, "policy declaration recorded");
        self.entries
            .insert(format!("declaration.{key}"), value.to_owned());
        self
    }

    /// Delta from `self` (base) to `head`: every added, removed or changed setting with old and new value.
    #[must_use]
    pub fn diff(&self, head: &Self) -> PolicyDelta {
        let mut changes = Vec::new();
        for (k, old) in &self.entries {
            match head.entries.get(k) {
                Some(new) if new == old => {}
                new => changes.push(PolicyChange {
                    key: k.clone(),
                    old: Some(old.clone()),
                    new: new.cloned(),
                }),
            }
        }
        for (k, new) in &head.entries {
            if !self.entries.contains_key(k) {
                changes.push(PolicyChange {
                    key: k.clone(),
                    old: None,
                    new: Some(new.clone()),
                });
            }
        }
        changes.sort_by(|a, b| a.key.cmp(&b.key));
        debug!(changes = changes.len(), "policy delta computed");
        PolicyDelta { changes }
    }
}
