//! LAYOUT003: a solved scene node whose rectangle extends beyond the viewport, so part of it is clipped. Off when the project has no scene files.

// frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_inputs, scene_subjects};
use crate::scene_files::{EPSILON, rect};

/// A scene node clipped by the viewport edge.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "LAYOUT003",
    slug = "node-clipped-by-viewport",
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
pub struct Layout003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Layout003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(scenes) = host.scenes() else {
            return;
        };
        for file in &scenes.files {
            let (vw, vh) = (file.solve.viewport_width, file.solve.viewport_height);
            for node in &file.solve.nodes {
                let (left, top, right, bottom) = rect(node);
                if left < -EPSILON
                    || top < -EPSILON
                    || right > vw + EPSILON
                    || bottom > vh + EPSILON
                {
                    tracing::debug!(path = %file.path, id = %node.id, "LAYOUT003: clipped by viewport");
                    out.fire_in(
                        &file.path,
                        file.offset_of(&node.id),
                        format!(
                            "'{}' ({left}, {top}, {right}, {bottom}) is clipped by the {vw}x{vh} viewport",
                            node.id
                        ),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Layout003 {
    fn subjects(&self, host: &P) -> usize {
        scene_subjects(host)
    }
}
