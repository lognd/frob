//! SCENE002: a scene element has no `data-id`, or repeats one already used in the same scene. Off when the project has no scene documents.

// frob:ticket 01M5H30AQNZSC77EY70P28KM3V

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};

/// a scene element has no `data-id`, or repeats one already used in the same scene.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SCENE002",
    slug = "scene-data-id-invalid",
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
pub struct Scene002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Scene002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            for hit in crunk_scene::data_id_problems(&file.doc) {
                let message = match &hit.problem {
                    crunk_scene::DataIdProblem::Missing => format!(
                        "<{}> on line {} has no data-id; every scene element needs a stable one",
                        hit.tag, hit.line
                    ),
                    crunk_scene::DataIdProblem::Duplicate { id, first_line } => format!(
                        "data-id '{id}' on <{}> (line {}) is already used on line {first_line}; ids must be unique per scene",
                        hit.tag, hit.line
                    ),
                };
                tracing::debug!(path = %file.path, line = hit.line, "SCENE002: data-id problem");
                out.fire_in(&file.path, hit.offset, message);
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Scene002 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
