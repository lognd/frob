//! The rule registry built from `inventory`.

use std::collections::BTreeMap;
use std::sync::OnceLock;

use crate::meta::{RuleEntry, RuleMeta};

/// A registry integrity failure.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum RegistryError {
    /// Two rules declare the same id.
    #[error("duplicate rule id {id}: declared in `{first}` and `{second}`")]
    DuplicateId {
        /// The clashing id.
        id: &'static str,
        /// Module path of the first declaration.
        first: &'static str,
        /// Module path of the second declaration.
        second: &'static str,
    },
    /// Two rules declare the same slug.
    #[error("duplicate rule slug `{slug}`: declared in `{first}` and `{second}`")]
    DuplicateSlug {
        /// The clashing slug.
        slug: &'static str,
        /// Module path of the first declaration.
        first: &'static str,
        /// Module path of the second declaration.
        second: &'static str,
    },
}

/// All known rules, sorted by id, with lookup by id or slug.
#[derive(Debug)]
pub struct Registry {
    rules: Vec<&'static RuleMeta>,
}

impl Registry {
    /// Build a registry from explicit metadata (sorted by id, stable).
    pub fn from_metas(metas: impl IntoIterator<Item = &'static RuleMeta>) -> Self {
        let mut rules: Vec<_> = metas.into_iter().collect();
        rules.sort_by_key(|m| m.id);
        Self { rules }
    }

    /// The process-wide registry of every `#[derive(Rule)]` linked in.
    pub fn global() -> &'static Registry {
        static GLOBAL: OnceLock<Registry> = OnceLock::new();
        GLOBAL.get_or_init(|| Registry::from_metas(inventory::iter::<RuleEntry>().map(|e| e.meta)))
    }

    /// Iterate rules in id order.
    pub fn iter(&self) -> impl Iterator<Item = &'static RuleMeta> + '_ {
        self.rules.iter().copied()
    }

    /// Number of registered rules (duplicates included).
    pub fn len(&self) -> usize {
        self.rules.len()
    }

    /// True when no rule is registered.
    pub fn is_empty(&self) -> bool {
        self.rules.is_empty()
    }

    /// Look up a rule by exact id.
    pub fn by_id(&self, id: &str) -> Option<&'static RuleMeta> {
        self.iter().find(|m| m.id == id)
    }

    /// Look up a rule by slug.
    pub fn by_slug(&self, slug: &str) -> Option<&'static RuleMeta> {
        self.iter().find(|m| m.slug == slug)
    }

    /// Check that ids and slugs are unique.
    ///
    /// # Errors
    ///
    /// Returns the first clash, naming both declaring modules.
    pub fn verify_unique(&self) -> Result<(), RegistryError> {
        let mut ids: BTreeMap<&str, &'static RuleMeta> = BTreeMap::new();
        let mut slugs: BTreeMap<&str, &'static RuleMeta> = BTreeMap::new();
        for m in self.iter() {
            if let Some(prev) = ids.insert(m.id, m) {
                return Err(RegistryError::DuplicateId {
                    id: m.id,
                    first: prev.module,
                    second: m.module,
                });
            }
            if let Some(prev) = slugs.insert(m.slug, m) {
                return Err(RegistryError::DuplicateSlug {
                    slug: m.slug,
                    first: prev.module,
                    second: m.module,
                });
            }
        }
        Ok(())
    }
}
