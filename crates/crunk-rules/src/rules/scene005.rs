//! SCENE005: a scene document cannot be loaded, or its name repeats. Off when the project has no scene documents.

// frob:ticket 01M5H30AT7FM2BAXCTTDEGWV6J

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, inapplicable_without, scene_doc_load_subjects};

/// a scene document cannot be loaded, or its name repeats.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SCENE005",
    slug = "scene-document-unloadable",
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
pub struct Scene005;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Scene005 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for problem in &facts.problems {
            tracing::debug!(path = %problem.path, kind = ?problem.kind, "SCENE005: scene document problem");
            out.fire_in(&problem.path, 0, problem.message.clone());
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        inapplicable_without(
            host,
            scene_doc_load_subjects(host),
            "no design/scenes/*.scene.html files",
        )
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Scene005 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_load_subjects(host)
    }
}
