//! SCENE001: a scene document styles an element with a CSS property outside the supported scene subset. Off when the project has no scene documents.

// frob:ticket 01M5H30AMSB0THE4GW322D4K54

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};

/// A scene using a CSS property the scene renderer does not support.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SCENE001",
    slug = "scene-property-unsupported",
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
pub struct Scene001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Scene001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            for hit in crunk_scene::unsupported_properties(&file.doc) {
                let message = format!(
                    "scene property '{}' is not supported (on {}, line {}): {}",
                    hit.property,
                    file.element_label(hit.offset),
                    hit.line,
                    hit.message
                );
                tracing::debug!(path = %file.path, property = %hit.property, "SCENE001: unsupported property");
                out.fire_in(&file.path, hit.offset, message);
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Scene001 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
