//! LAYOUT001: a solved scene node whose rectangle extends beyond its parent's (content overflow), read from the crunk-layout solve of each `design/scenes/*.scene.html`. Off when the project has no scene files.

// frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62

use gob_rules::{Measured, Out, RepoRule, rule};

use crunk_layout::findings::{ChildOverflow, child_overflows, rect};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};

/// A scene node that overflows its parent's rectangle.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "LAYOUT001",
    slug = "child-overflows-parent",
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
pub struct Layout001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Layout001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(facts) = host.scene_docs() else {
            return;
        };
        for file in &facts.files {
            let Some(solve) = file.solve() else {
                continue;
            };
            for ChildOverflow { node, parent } in child_overflows(solve) {
                let (l, t, r, b) = rect(node);
                let (pl, pt, pr, pb) = rect(parent);
                tracing::debug!(path = %file.path, id = %node.id, "LAYOUT001: overflows parent");
                out.fire_in(
                    &file.path,
                    file.offset_of(&node.id),
                    format!(
                        "'{}' ({l}, {t}, {r}, {b}) overflows its parent '{}' ({pl}, {pt}, {pr}, {pb}) in a {}x{} viewport",
                        node.id, parent.id, solve.viewport_width, solve.viewport_height
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Layout001 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
