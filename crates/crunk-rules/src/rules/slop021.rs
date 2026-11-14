//! SLOP021: A card nested three deep in cards, or a section whose children are mostly cards. Advisory; decided at T1 (the layout solve).

// frob:ticket 01M4CXTCXCKKPRDHXEEZ2NK7PP

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};
use crate::scene_docs::SceneDocFile;
use crate::slop_layout::{SceneView, card_nesting};

/// A card nested three deep in cards, or a section whose children are mostly cards.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SLOP021",
    slug = "card-nesting",
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
pub struct Slop021;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Slop021 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            if let Err(why) = file.solve() {
                tracing::warn!(path = %file.path, %why, "SLOP021: scene does not solve; geometry unjudged");
                out.unresolved_in(&file.path, 0, SceneDocFile::unsolved_message(why));
            }
            let view = SceneView::new(file);
            for tell in card_nesting(&view) {
                tracing::debug!(path = %file.path, "SLOP021: fires");
                out.fire_in(&file.path, tell.offset, tell.message);
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Slop021 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
