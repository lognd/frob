//! SLOP026: Running text over three lines (or 160 characters, unsolved) with `text-align: center`. Advisory; decided at T1 (the layout solve).

// frob:ticket 01M4CXTCXCKKPRDHXEEZ2NK7PP

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};
use crate::scene_docs::SceneDocFile;
use crate::slop_layout::{SceneView, centred_long_text};

/// Running text over three lines (or 160 characters, unsolved) with `text-align: center`.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "SLOP026",
    slug = "centred-long-text",
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
pub struct Slop026;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Slop026 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            if let Err(why) = file.solve() {
                tracing::warn!(path = %file.path, %why, "SLOP026: scene does not solve; geometry unjudged");
                out.unresolved_in(&file.path, 0, SceneDocFile::unsolved_message(why));
            }
            let view = SceneView::new(file);
            for tell in centred_long_text(&view) {
                tracing::debug!(path = %file.path, "SLOP026: fires");
                out.fire_in(&file.path, tell.offset, tell.message);
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Slop026 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
