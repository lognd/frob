//! SCENE004: a scene stylesheet uses an at-rule other than `@media`. Off when the project has no scene documents.

// frob:ticket 01M5H30AQNZSC77EY70P28KM3V

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};

/// a scene stylesheet uses an at-rule other than `@media`.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SCENE004",
    slug = "scene-at-rule-unsupported",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Scene004;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Scene004 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            for hit in crunk_scene::unsupported_at_rules(&file.doc) {
                let message = format!(
                    "at-rule '@{}' (line {}) is not supported in a scene; only @media is",
                    hit.name, hit.line
                );
                tracing::debug!(path = %file.path, at_rule = %hit.name, "SCENE004: unsupported at-rule");
                out.fire_in(&file.path, hit.offset, message);
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Scene004 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
