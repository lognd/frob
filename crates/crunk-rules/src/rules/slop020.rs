//! SLOP020: Three or more sibling cards that each run icon, heading, paragraph with one structure and one size. Advisory; decided at T1 (the layout solve).

// frob:ticket 01M4CXTCXCKKPRDHXEEZ2NK7PP

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};
use crate::slop_layout::{SceneView, identical_cards};

/// Three or more sibling cards that each run icon, heading, paragraph with one structure and one size.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SLOP020",
    slug = "identical-icon-cards",
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
pub struct Slop020;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Slop020 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            let view = SceneView::new(file);
            for tell in identical_cards(&view) {
                tracing::debug!(path = %file.path, "SLOP020: fires");
                out.fire_in(&file.path, tell.offset, tell.message);
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Slop020 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
