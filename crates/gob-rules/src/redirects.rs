//! Rename and retirement tables for rule ids and slugs (the ruff `redirects` idea, ~67J8R53).
//!
//! A rule that is renamed keeps working under its old id or slug: config (`[rules]`), directives
//! and `--rule` arguments are resolved through [`Redirects`]. A rule that is deleted keeps its id
//! reserved so a later rule can never silently inherit the old id's suppressions. The central
//! tables [`RENAMED_IDS`], [`RENAMED_SLUGS`] and [`RETIRED_IDS`] are the one reviewed place for
//! legacy (`#[derive(Rule)]`) rules; per-crate `retired.rs` tables are merged in through
//! [`Redirects::with_indexes`].

use std::collections::{BTreeMap, BTreeSet};

use crate::index::RuleIndex;

/// `(old id, new id)` pairs of renamed legacy rules; the old id stays resolvable and reserved.
pub const RENAMED_IDS: &[(&str, &str)] = &[];

/// `(old slug, new slug)` pairs of renamed rules.
pub const RENAMED_SLUGS: &[(&str, &str)] = &[];

/// Ids of deleted legacy rules; they may never be reused.
pub const RETIRED_IDS: &[&str] = &[];

/// A redirect table inconsistency.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum RedirectError {
    /// A live rule id is also an old (renamed) id, so the redirect would be shadowed.
    #[error("renamed id `{old}` (now `{new}`) is also a live rule id, declared in `{module}`")]
    ShadowedId {
        /// The old id.
        old: String,
        /// What it was renamed to.
        new: String,
        /// Module that declares the live rule using the old id.
        module: String,
    },
    /// A live rule slug is also an old (renamed) slug.
    #[error("renamed slug `{old}` (now `{new}`) is also a live rule slug, declared in `{module}`")]
    ShadowedSlug {
        /// The old slug.
        old: String,
        /// What it was renamed to.
        new: String,
        /// Module that declares the live rule using the old slug.
        module: String,
    },
    /// A new rule reuses the id of a removed rule.
    #[error("rule id `{id}` is retired and may not be reused (declared in `{module}`)")]
    RetiredIdReused {
        /// The reserved id.
        id: String,
        /// Module that declares the new rule.
        module: String,
    },
    /// A rename points at an id or slug that is neither live nor itself redirected.
    #[error("`{old}` is renamed to `{new}`, which is not a live rule")]
    DanglingTarget {
        /// The old name.
        old: String,
        /// The missing target.
        new: String,
    },
}

/// The merged rename and retirement tables, consulted before a lookup gives up.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Redirects {
    ids: BTreeMap<String, String>,
    slugs: BTreeMap<String, String>,
    retired: BTreeSet<String>,
}

/// Longest rename chain followed; a longer one is a cycle and resolves to nothing.
const MAX_HOPS: usize = 8;

impl Redirects {
    /// The central tables ([`RENAMED_IDS`], [`RENAMED_SLUGS`], [`RETIRED_IDS`]).
    #[must_use]
    pub fn builtin() -> Self {
        Self::from_pairs(
            RENAMED_IDS.iter().copied(),
            RENAMED_SLUGS.iter().copied(),
            RETIRED_IDS.iter().copied(),
        )
    }

    /// Build a table from explicit `(old, new)` id and slug pairs and retired ids.
    pub fn from_pairs<'a>(
        ids: impl IntoIterator<Item = (&'a str, &'a str)>,
        slugs: impl IntoIterator<Item = (&'a str, &'a str)>,
        retired: impl IntoIterator<Item = &'a str>,
    ) -> Self {
        let table = Self {
            ids: ids
                .into_iter()
                .map(|(o, n)| (o.to_owned(), n.to_owned()))
                .collect(),
            slugs: slugs
                .into_iter()
                .map(|(o, n)| (o.to_owned(), n.to_owned()))
                .collect(),
            retired: retired.into_iter().map(str::to_owned).collect(),
        };
        tracing::debug!(
            renamed_ids = table.ids.len(),
            renamed_slugs = table.slugs.len(),
            retired = table.retired.len(),
            "redirect table built"
        );
        table
    }

    /// Merge the `renamed` and `retired` tables of per-crate rule indexes into this table.
    #[must_use]
    pub fn with_indexes(mut self, indexes: &[&RuleIndex]) -> Self {
        for ix in indexes {
            for (old, new) in ix.renamed {
                self.ids.insert((*old).to_owned(), (*new).to_owned());
            }
            self.retired
                .extend(ix.retired.iter().map(|r| (*r).to_owned()));
        }
        self
    }

    /// Follow renames from `id` to its current id; `None` when `id` was never renamed or the chain loops.
    #[must_use]
    pub fn resolve_id(&self, id: &str) -> Option<&str> {
        Self::follow(&self.ids, id)
    }

    /// Follow slug renames from `slug` to its current slug.
    #[must_use]
    pub fn resolve_slug(&self, slug: &str) -> Option<&str> {
        Self::follow(&self.slugs, slug)
    }

    /// True when `id` belonged to a deleted rule and is reserved.
    #[must_use]
    pub fn is_retired(&self, id: &str) -> bool {
        self.retired.contains(id)
    }

    fn follow<'a>(map: &'a BTreeMap<String, String>, start: &str) -> Option<&'a str> {
        let mut current = map.get(start)?;
        for _ in 0..MAX_HOPS {
            match map.get(current.as_str()) {
                Some(next) => current = next,
                None => return Some(current.as_str()),
            }
        }
        tracing::warn!(start, "rename chain does not terminate");
        None
    }

    /// Check the table against the live rules, given as `(id, slug, declaring module)`.
    ///
    /// # Errors
    /// Every inconsistency: a live id or slug shadowing an old name, a retired id reused, and a
    /// rename target that is not live.
    pub fn check_live<'a>(
        &self,
        live: impl IntoIterator<Item = (&'a str, &'a str, &'a str)>,
    ) -> Result<(), Vec<RedirectError>> {
        let live: Vec<_> = live.into_iter().collect();
        let mut errors = Vec::new();
        for (id, slug, module) in &live {
            if let Some(new) = self.ids.get(*id) {
                errors.push(RedirectError::ShadowedId {
                    old: (*id).to_owned(),
                    new: new.clone(),
                    module: (*module).to_owned(),
                });
            }
            if let Some(new) = self.slugs.get(*slug) {
                errors.push(RedirectError::ShadowedSlug {
                    old: (*slug).to_owned(),
                    new: new.clone(),
                    module: (*module).to_owned(),
                });
            }
            if self.retired.contains(*id) {
                errors.push(RedirectError::RetiredIdReused {
                    id: (*id).to_owned(),
                    module: (*module).to_owned(),
                });
            }
        }
        for (old, new) in &self.ids {
            let target = self.resolve_id(old).unwrap_or(new);
            if !live.iter().any(|(id, _, _)| *id == target) {
                errors.push(RedirectError::DanglingTarget {
                    old: old.clone(),
                    new: target.to_owned(),
                });
            }
        }
        for (old, new) in &self.slugs {
            let target = self.resolve_slug(old).unwrap_or(new);
            if !live.iter().any(|(_, slug, _)| *slug == target) {
                errors.push(RedirectError::DanglingTarget {
                    old: old.clone(),
                    new: target.to_owned(),
                });
            }
        }
        if errors.is_empty() {
            Ok(())
        } else {
            tracing::error!(problems = errors.len(), "redirect table inconsistent");
            Err(errors)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn table() -> Redirects {
        Redirects::from_pairs(
            [("OLD001", "MID001"), ("MID001", "NEW001")],
            [("old-slug", "new-slug")],
            ["GONE001"],
        )
    }

    // frob:tests renamed_ids_follow_the_chain
    #[test]
    fn renamed_ids_follow_the_chain() {
        let t = table();
        assert_eq!(t.resolve_id("OLD001"), Some("NEW001"));
        assert_eq!(t.resolve_id("NEW001"), None);
        assert_eq!(t.resolve_slug("old-slug"), Some("new-slug"));
        assert!(t.is_retired("GONE001"));
    }

    // frob:tests a_rename_loop_resolves_to_nothing
    #[test]
    fn a_rename_loop_resolves_to_nothing() {
        let t = Redirects::from_pairs([("A001", "B001"), ("B001", "A001")], [], []);
        assert_eq!(t.resolve_id("A001"), None);
    }

    // frob:tests live_names_may_not_shadow_a_redirect_or_reuse_a_retired_id
    #[test]
    fn live_names_may_not_shadow_a_redirect_or_reuse_a_retired_id() {
        let live = [
            ("NEW001", "new-slug", "m::new"),
            ("OLD001", "x", "m::shadow"),
            ("GONE001", "y", "m::reuse"),
        ];
        let errors = table().check_live(live).unwrap_err();
        assert!(errors.contains(&RedirectError::ShadowedId {
            old: "OLD001".into(),
            new: "MID001".into(),
            module: "m::shadow".into()
        }));
        assert!(errors.contains(&RedirectError::RetiredIdReused {
            id: "GONE001".into(),
            module: "m::reuse".into()
        }));
    }

    // frob:tests a_consistent_table_passes
    #[test]
    fn a_consistent_table_passes() {
        let live = [("NEW001", "new-slug", "m::new")];
        assert_eq!(table().check_live(live), Ok(()));
    }

    // frob:tests the_builtin_tables_are_consistent_on_their_own
    #[test]
    fn the_builtin_tables_are_consistent_on_their_own() {
        let t = Redirects::builtin();
        for (old, _) in RENAMED_IDS {
            assert!(!t.is_retired(old), "{old} is both renamed and retired");
        }
    }
}
