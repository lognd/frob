//! The explicit per-product registry of rule crates, checked against what actually linked (~67J8R53).
//!
//! The reviewed list [`PRODUCT_CRATES`] says which crates contribute rules to which product.
//! [`check_registry`] compares it with the legacy `inventory` entries and the per-crate
//! [`RuleIndex`] values, so a crate dropped from the build (or a rule crate nobody listed) is a
//! test failure that names the crate, instead of a silently shorter rule set. This replaces the
//! link-time "anchor" calls that used to keep the linker from discarding inventory entries.

use std::collections::BTreeMap;

use crate::index::RuleIndex;
use crate::meta::RuleMeta;

/// One product and every crate that contributes rules to it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ProductCrates {
    /// Product namespace (`frob`, `grimble`, `crunk`).
    pub product: &'static str,
    /// Cargo package names of the rule-bearing crates.
    pub crates: &'static [&'static str],
}

/// The reviewed list of rule crates per product; adding a rule crate means adding it here.
pub const PRODUCT_CRATES: &[ProductCrates] = &[
    ProductCrates {
        product: "frob",
        crates: &[
            "frob-tests",
            "frob-ack",
            "frob-obligations",
            "frob-ledger",
            "frob-pm",
            "frob-release",
            "frob-lease",
            "gob-config",
            "frob-check",
            "gob-check",
            "gob-directives",
        ],
    },
    ProductCrates {
        product: "grimble",
        crates: &[
            "grimble-model",
            "grimble-bind",
            "grimble-arch",
            "grimble-lints",
            "grimble-ci",
            "grimble-capabilities",
            "grimble-check",
        ],
    },
    ProductCrates {
        product: "crunk",
        crates: &["crunk-rules", "crunk-check"],
    },
];

/// A registry inconsistency.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum ProductRegistryError {
    /// A declared crate contributed no rule: it was dropped from the build or its rules are gone.
    #[error(
        "product `{product}` declares rule crate `{krate}`, but it contributes no rules (dropped from the build?)"
    )]
    MissingCrate {
        /// Product that lists the crate.
        product: String,
        /// The missing crate.
        krate: String,
    },
    /// A rule comes from a crate no product lists.
    #[error(
        "rule `{rule}` (module `{module}`) is in crate `{krate}`, which product `{product}` does not list"
    )]
    UndeclaredCrate {
        /// Product the rule claims.
        product: String,
        /// The unlisted crate.
        krate: String,
        /// The rule id.
        rule: String,
        /// The declaring module.
        module: String,
    },
    /// Two rules, in any mix of declaration styles, share an id.
    #[error("duplicate rule id {id}: declared at `{first}` and `{second}`")]
    DuplicateId {
        /// The clashing id.
        id: String,
        /// First declaring site.
        first: String,
        /// Second declaring site.
        second: String,
    },
    /// Two rules share a slug.
    #[error("duplicate rule slug `{slug}`: declared at `{first}` and `{second}`")]
    DuplicateSlug {
        /// The clashing slug.
        slug: String,
        /// First declaring site.
        first: String,
        /// Second declaring site.
        second: String,
    },
}

/// The crate a `module_path!()` belongs to, as a cargo package name.
#[must_use]
pub fn crate_of_module(module: &str) -> String {
    module
        .split("::")
        .next()
        .unwrap_or(module)
        .replace('_', "-")
}

/// Check the linked rules against `declared`; every problem is returned.
///
/// `metas` are the legacy `#[derive(Rule)]` entries, `indexes` the `#[rule]` crates' indexes.
/// A partial test binary passes only the entries of `declared` it links.
///
/// # Errors
/// Missing or undeclared crates and ids or slugs declared twice across both styles.
pub fn check_registry(
    declared: &[ProductCrates],
    metas: &[&RuleMeta],
    indexes: &[&RuleIndex],
) -> Result<(), Vec<ProductRegistryError>> {
    let mut errors = Vec::new();
    let all_declared = |krate: &str| declared.iter().any(|p| p.crates.contains(&krate));

    for p in declared {
        for krate in p.crates {
            let in_index = indexes.iter().any(|ix| ix.krate == *krate);
            let in_meta = metas
                .iter()
                .any(|m| m.product == p.product && crate_of_module(m.module) == *krate);
            if !in_index && !in_meta {
                errors.push(ProductRegistryError::MissingCrate {
                    product: p.product.to_owned(),
                    krate: (*krate).to_owned(),
                });
            }
        }
    }
    for m in metas {
        let krate = crate_of_module(m.module);
        let listed = declared
            .iter()
            .any(|p| p.product == m.product && p.crates.contains(&krate.as_str()));
        if !listed {
            errors.push(ProductRegistryError::UndeclaredCrate {
                product: m.product.to_owned(),
                krate,
                rule: m.id.to_owned(),
                module: m.module.to_owned(),
            });
        }
    }
    for ix in indexes {
        if !all_declared(ix.krate) {
            errors.push(ProductRegistryError::UndeclaredCrate {
                product: "?".to_owned(),
                krate: ix.krate.to_owned(),
                rule: ix.metas.first().map_or("-", |d| d.id).to_owned(),
                module: ix.krate.to_owned(),
            });
        }
    }

    let mut ids: BTreeMap<&str, String> = BTreeMap::new();
    let mut slugs: BTreeMap<&str, String> = BTreeMap::new();
    // A legacy row that mirrors an indexed declaration (same id and slug) is a bridge, not a clash.
    let bridged = |m: &RuleMeta| {
        indexes
            .iter()
            .any(|ix| ix.metas.iter().any(|d| d.id == m.id && d.slug == m.slug))
    };
    let sites = metas
        .iter()
        .filter(|m| !bridged(m))
        .map(|m| (m.id, m.slug, m.module.to_owned()))
        .chain(indexes.iter().flat_map(|ix| {
            ix.metas.iter().map(|d| {
                (
                    d.id,
                    d.slug,
                    format!("{} ({}:{})", ix.krate, d.file, d.line),
                )
            })
        }));
    for (id, slug, site) in sites {
        if let Some(first) = ids.insert(id, site.clone()) {
            errors.push(ProductRegistryError::DuplicateId {
                id: id.to_owned(),
                first,
                second: site.clone(),
            });
        }
        if let Some(first) = slugs.insert(slug, site.clone()) {
            errors.push(ProductRegistryError::DuplicateSlug {
                slug: slug.to_owned(),
                first,
                second: site,
            });
        }
    }
    if errors.is_empty() {
        tracing::debug!(products = declared.len(), "product registry consistent");
        Ok(())
    } else {
        tracing::error!(problems = errors.len(), "product registry inconsistent");
        Err(errors)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::meta::{FixKind, Needs, Polarity, Scope, Severity, Tier};

    const fn meta(id: &'static str, slug: &'static str, module: &'static str) -> RuleMeta {
        RuleMeta {
            id,
            slug,
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
            needs: Needs::Structural,
            version: 1,
            since: "0.1.0",
            module,
        }
    }

    static A: RuleMeta = meta("AAA001", "a-rule", "crate_a::rules");
    static B: RuleMeta = meta("AAA002", "b-rule", "crate_b::rules");
    static CLASH: RuleMeta = meta("AAA001", "c-rule", "crate_b::other");
    const DECLARED: &[ProductCrates] = &[ProductCrates {
        product: "frob",
        crates: &["crate-a", "crate-b"],
    }];

    // frob:tests a_dropped_crate_fails_naming_it
    #[test]
    fn a_dropped_crate_fails_naming_it() {
        let errors = check_registry(DECLARED, &[&A], &[]).unwrap_err();
        assert_eq!(
            errors,
            vec![ProductRegistryError::MissingCrate {
                product: "frob".into(),
                krate: "crate-b".into()
            }]
        );
        assert!(errors[0].to_string().contains("crate-b"));
    }

    // frob:tests an_unlisted_crate_fails_naming_it
    #[test]
    fn an_unlisted_crate_fails_naming_it() {
        let errors = check_registry(&DECLARED[..0], &[&A], &[]).unwrap_err();
        assert!(
            matches!(&errors[0], ProductRegistryError::UndeclaredCrate { krate, .. } if krate == "crate-a")
        );
    }

    // frob:tests duplicate_ids_name_both_declaring_modules
    #[test]
    fn duplicate_ids_name_both_declaring_modules() {
        let errors = check_registry(DECLARED, &[&A, &B, &CLASH], &[]).unwrap_err();
        let text = errors[0].to_string();
        assert!(
            text.contains("AAA001")
                && text.contains("crate_a::rules")
                && text.contains("crate_b::other"),
            "{text}"
        );
    }

    // frob:tests duplicate_slugs_name_both_declaring_modules
    #[test]
    fn duplicate_slugs_name_both_declaring_modules() {
        static DUP: RuleMeta = meta("AAA009", "a-rule", "crate_b::dup");
        let errors = check_registry(DECLARED, &[&A, &B, &DUP], &[]).unwrap_err();
        let text = errors[0].to_string();
        assert!(
            text.contains("a-rule")
                && text.contains("crate_a::rules")
                && text.contains("crate_b::dup"),
            "{text}"
        );
    }

    // frob:tests a_legacy_row_mirroring_an_indexed_rule_is_not_a_clash
    #[test]
    fn a_legacy_row_mirroring_an_indexed_rule_is_not_a_clash() {
        static IX: RuleIndex = RuleIndex {
            krate: "crate-b",
            metas: &[],
            renamed: &[],
            retired: &[],
        };
        assert_eq!(check_registry(DECLARED, &[&A, &B], &[&IX]), Ok(()));
    }

    // frob:tests a_complete_registry_passes
    #[test]
    fn a_complete_registry_passes() {
        assert_eq!(check_registry(DECLARED, &[&A, &B], &[]), Ok(()));
    }

    // frob:tests crate_of_module_maps_underscores
    #[test]
    fn crate_of_module_maps_underscores() {
        assert_eq!(crate_of_module("frob_check::grl::x"), "frob-check");
    }
}
