//! LAYOUT002: two sibling scene nodes whose solved rectangles overlap with positive area (content collision), read from the crunk-layout solve of each `design/scenes/*.scene.html`. Off when the project has no scene files.

// frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62

use gob_rules::{Measured, Out, RepoRule, rule};

use crunk_layout::findings::{SiblingOverlap, sibling_overlaps};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};

/// Two sibling scene nodes whose rectangles overlap.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "LAYOUT002",
    slug = "siblings-overlap",
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
pub struct Layout002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Layout002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            let Some(solve) = file.solve() else {
                continue;
            };
            for SiblingOverlap { a, b, across, down } in sibling_overlaps(solve) {
                tracing::debug!(path = %file.path, a = %a.id, b = %b.id, "LAYOUT002: siblings overlap");
                out.fire_in(
                    &file.path,
                    file.offset_of(&b.id),
                    format!(
                        "'{}' overlaps its sibling '{}' by {across}x{down} px",
                        b.id, a.id
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Layout002 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
