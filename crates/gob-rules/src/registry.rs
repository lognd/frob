//! The rule registry built from `inventory`.

use std::collections::{BTreeMap, BTreeSet};
use std::sync::OnceLock;

use serde::Serialize;

use crate::meta::{FixKind, Polarity, Provenance, RuleEntry, RuleMeta, Scope, Severity, Tier};

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

/// All known rules (std and loaded packs), sorted by id, with lookup by id or slug.
///
/// frob:ticket 01M3ZX7FKFSHB8KZM2N4CNF0P9
#[derive(Debug)]
pub struct Registry {
    rules: Vec<&'static RuleMeta>,
    provenance: Vec<Provenance>,
}

/// One `rules list --json` row; identical for std and pack rules except `pack`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct RuleRow {
    /// Rule id.
    pub id: &'static str,
    /// Kebab-case alias.
    pub slug: &'static str,
    /// Family prefix.
    pub family: &'static str,
    /// Product namespace.
    pub product: &'static str,
    /// Default severity.
    pub severity: Severity,
    /// One-line summary.
    pub summary: &'static str,
    /// Universal or language tier.
    pub tier: Tier,
    /// File or repo scope.
    pub scope: Scope,
    /// Fix kind.
    pub fix: FixKind,
    /// Polarity.
    pub polarity: Polarity,
    /// Required-Unresolved flag.
    pub must_measure: bool,
    /// Rule version.
    pub version: u32,
    /// Release the rule appeared in.
    pub since: &'static str,
    /// Provenance label: `std` or the pack name.
    pub pack: String,
}

/// The `[rules]` severity and disable settings, applied identically to every rule.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct RuleSettings {
    /// Ids switched off.
    pub disabled: BTreeSet<String>,
    /// Severity overrides by id.
    pub severity: BTreeMap<String, Severity>,
}

impl RuleSettings {
    /// The severity a rule runs at, or `None` when it is disabled; provenance plays no part.
    #[must_use]
    pub fn effective_severity(&self, meta: &RuleMeta) -> Option<Severity> {
        if self.disabled.contains(meta.id) {
            tracing::debug!(rule = meta.id, "rule disabled by [rules]");
            return None;
        }
        Some(self.severity.get(meta.id).copied().unwrap_or(meta.severity))
    }
}

impl Registry {
    /// Build a registry from explicit metadata (sorted by id, stable).
    pub fn from_metas(metas: impl IntoIterator<Item = &'static RuleMeta>) -> Self {
        Self::merged(metas, std::iter::empty())
    }

    /// Merge compiled-in (std) metadata with rules from loaded packs into one id-sorted view.
    pub fn merged(
        std: impl IntoIterator<Item = &'static RuleMeta>,
        packs: impl IntoIterator<Item = (String, &'static RuleMeta)>,
    ) -> Self {
        let mut all: Vec<(&'static RuleMeta, Provenance)> =
            std.into_iter().map(|m| (m, Provenance::Std)).collect();
        all.extend(packs.into_iter().map(|(p, m)| (m, Provenance::Pack(p))));
        all.sort_by_key(|(m, _)| m.id);
        tracing::debug!(rules = all.len(), "registry merged");
        let (rules, provenance) = all.into_iter().unzip();
        Self { rules, provenance }
    }

    /// Where the rule with this id came from, if registered.
    pub fn provenance(&self, id: &str) -> Option<&Provenance> {
        self.rules
            .iter()
            .position(|m| m.id == id)
            .map(|i| &self.provenance[i])
    }

    /// One uniform row per rule, in id order, for `rules list`.
    pub fn rows(&self) -> Vec<RuleRow> {
        self.rules
            .iter()
            .zip(&self.provenance)
            .map(|(m, p)| RuleRow {
                id: m.id,
                slug: m.slug,
                family: m.family,
                product: m.product,
                severity: m.severity,
                summary: m.summary,
                tier: m.tier,
                scope: m.scope,
                fix: m.fix,
                polarity: m.polarity,
                must_measure: m.must_measure,
                version: m.version,
                since: m.since,
                pack: p.label().to_owned(),
            })
            .collect()
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

#[cfg(test)]
mod tests {
    use super::*;

    static STD: RuleMeta = RuleMeta {
        id: "AAA001",
        slug: "std-rule",
        family: "AAA",
        product: "frob",
        severity: Severity::Error,
        summary: "s",
        explanation: "s",
        tier: Tier::Universal,
        scope: Scope::File,
        fix: FixKind::Manual,
        polarity: Polarity::Pplus,
        must_measure: false,
        needs: crate::meta::Needs::Structural,
        version: 1,
        since: "0.1.0",
        module: "std_mod",
    };
    static PLUG: RuleMeta = RuleMeta {
        id: "ZZZ001",
        slug: "plug-rule",
        family: "ZZZ",
        module: "plug_mod",
        ..STD
    };

    fn reg() -> Registry {
        Registry::merged([&STD], [("acme".to_owned(), &PLUG)])
    }

    // frob:tests registry_rows_differ_only_in_provenance
    #[test]
    fn registry_rows_differ_only_in_provenance() {
        let rows = reg().rows();
        let v: Vec<_> = rows
            .iter()
            .map(|r| serde_json::to_value(r).unwrap())
            .collect();
        let keys =
            |x: &serde_json::Value| x.as_object().unwrap().keys().cloned().collect::<Vec<_>>();
        assert_eq!(keys(&v[0]), keys(&v[1]));
        assert_eq!(v[0]["pack"], "std");
        assert_eq!(v[1]["pack"], "acme");
        assert_eq!(
            reg().provenance("ZZZ001"),
            Some(&Provenance::Pack("acme".into()))
        );
    }

    // frob:tests rules_settings_apply_identically
    #[test]
    fn rules_settings_apply_identically() {
        let mut s = RuleSettings::default();
        s.severity.insert("AAA001".into(), Severity::Warn);
        s.severity.insert("ZZZ001".into(), Severity::Warn);
        assert_eq!(s.effective_severity(&STD), Some(Severity::Warn));
        assert_eq!(s.effective_severity(&PLUG), Some(Severity::Warn));
        s.disabled.insert("AAA001".into());
        s.disabled.insert("ZZZ001".into());
        assert_eq!(s.effective_severity(&STD), None);
        assert_eq!(s.effective_severity(&PLUG), None);
    }
}
