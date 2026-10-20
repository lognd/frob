//! `CFG001`: a materialized knob is absent from the product file

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP

use gob_rules::{Out, RepoRule, rule};

use crate::host::ConfigHost;

/// A materialized knob is absent from the product file
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CFG001",
    slug = "missing-materialized-knob",
    severity = Error,
    polarity = Pminus,
    must_measure = false,
    scope = Repo,
    fix = Deterministic,
    applies = project,
    host = ConfigHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Cfg001;

/// The finding is raised by [`crate::check`] from the doctor, which reads the product file; this declaration registers the id.
impl<P: ?Sized + ConfigHost> RepoRule<P> for Cfg001 {
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

/// The registry row of `CFG001`, so renderers that read the global registry still resolve its slug.
// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP
static META: gob_rules::RuleMeta = gob_rules::RuleMeta {
    id: "CFG001",
    slug: "missing-materialized-knob",
    family: "CFG",
    product: "frob",
    severity: gob_rules::Severity::Error,
    summary: "A materialized config knob is missing from the product config file.",
    explanation: <Cfg001 as gob_rules::RuleDecl>::DEF.doc,
    tier: gob_rules::Tier::Universal,
    scope: gob_rules::Scope::Repo,
    fix: gob_rules::FixKind::Deterministic,
    polarity: gob_rules::Polarity::Pminus,
    must_measure: false,
    needs: gob_rules::Needs::Structural,
    version: 1,
    since: "0.532.0",
    module: "gob_config",
};

gob_rules::inventory::submit! { gob_rules::RuleEntry::new(&META) }

#[cfg(test)]
mod tests {
    use super::*;

    /// The registry row stays in step with the declaration.
    #[test]
    fn the_registry_row_matches_the_declaration() {
        // frob:tests crates/gob-config/src/rules/cfg001.rs::Cfg001
        let def = <Cfg001 as gob_rules::RuleDecl>::DEF;
        assert_eq!(META.id, def.id);
        assert_eq!(META.slug, def.slug);
        assert_eq!(META.summary, def.summary());
        assert_eq!(META.severity, def.severity);
        assert_eq!(META.version, def.version);
    }
}
