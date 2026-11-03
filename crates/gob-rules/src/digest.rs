//! A digest of rule declarations, so a cache keyed on it misses when any verdict-relevant field changes.
// frob:ticket 01M6BFHB1VR63SY8VFQ6M9E4NB

use std::fmt::Write as _;

use crate::decl::RuleDef;
use crate::meta::RuleMeta;

/// Hex blake3 of `text`, the shared tail of both digests.
fn hash(text: &str) -> String {
    blake3::hash(text.as_bytes()).to_hex().to_string()
}

/// A digest of everything about `defs` that can change a verdict: id, version, severity, gates, nature, polarity, needs, scope, applicability and release.
///
/// A cache engine fingerprint that is only the crate version misses nothing when a rule is
/// added, removed, re-versioned or re-leveled; folding this into the key makes it miss.
pub fn rules_digest<'a>(defs: impl IntoIterator<Item = &'a RuleDef>) -> String {
    let mut text = String::new();
    for d in defs {
        writeln!(
            text,
            "{}|{}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{}",
            d.id,
            d.version,
            d.severity,
            d.gates,
            d.nature,
            d.polarity,
            d.must_measure,
            d.needs,
            d.scope,
            d.applies,
            d.since
        )
        .ok();
    }
    hash(&text)
}

/// [`rules_digest`] for the legacy `#[derive(Rule)]` declarations, over the fields a verdict depends on.
pub fn metas_digest<'a>(metas: impl IntoIterator<Item = &'a RuleMeta>) -> String {
    let mut text = String::new();
    for m in metas {
        writeln!(
            text,
            "{}|{}|{:?}|{:?}|{:?}|{:?}|{:?}|{:?}|{}",
            m.id,
            m.version,
            m.severity,
            m.polarity,
            m.must_measure,
            m.needs,
            m.scope,
            m.tier,
            m.since
        )
        .ok();
    }
    hash(&text)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::meta::{FixKind, Needs, Polarity, Scope, Severity, Tier};

    /// A rule definition at `version`, otherwise inert.
    const fn def(version: u32) -> RuleDef {
        RuleDef {
            id: "XXX001",
            version,
            ..RuleDef::POISONED
        }
    }

    // frob:tests crates/gob-rules/src/digest.rs::rules_digest
    /// The digest is stable for one table and changes when a rule is re-versioned or added.
    #[test]
    fn rules_digest_tracks_the_table() {
        let (v1, v2) = (def(1), def(2));
        let a = rules_digest([&v1]);
        assert_eq!(a, rules_digest([&v1]));
        assert_ne!(a, rules_digest([&v2]));
        assert_ne!(a, rules_digest([&v1, &v2]));
    }

    /// A legacy rule declaration with `version` and `severity`, otherwise fixed.
    const fn meta(version: u32, severity: Severity) -> RuleMeta {
        RuleMeta {
            id: "AAA001",
            slug: "a-rule",
            family: "AAA",
            product: "frob",
            severity,
            summary: "s",
            explanation: "s",
            tier: Tier::Universal,
            scope: Scope::File,
            fix: FixKind::Manual,
            polarity: Polarity::Pplus,
            must_measure: false,
            needs: Needs::Structural,
            version,
            since: "0.1.0",
            module: "m",
        }
    }

    // frob:tests crates/gob-rules/src/digest.rs::metas_digest
    /// The legacy digest is stable and changes when a derive rule's version or severity changes.
    #[test]
    fn metas_digest_tracks_the_registry() {
        let base = meta(1, Severity::Error);
        let a = metas_digest([&base]);
        assert_eq!(a, metas_digest([&base]));
        assert_ne!(a, metas_digest([&meta(2, Severity::Error)]));
        assert_ne!(a, metas_digest([&meta(1, Severity::Unresolved)]));
        assert_ne!(a, metas_digest([]));
    }
}
