//! SCENE003: a scene uses a lowercase tag outside the scene dialect (components are capitalised). Off when the project has no scene documents.

// frob:ticket 01M5H30AQNZSC77EY70P28KM3V

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};

/// a scene uses a lowercase tag outside the scene dialect (components are capitalised).
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SCENE003",
    slug = "scene-tag-unknown",
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
pub struct Scene003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Scene003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            for hit in crunk_scene::unknown_tags(&file.doc) {
                let message = format!(
                    "tag <{}> (line {}) is not in the scene dialect; use a supported HTML tag or a capitalised component",
                    hit.tag, hit.line
                );
                tracing::debug!(path = %file.path, tag = %hit.tag, "SCENE003: unknown tag");
                out.fire_in(&file.path, hit.offset, message);
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Scene003 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
