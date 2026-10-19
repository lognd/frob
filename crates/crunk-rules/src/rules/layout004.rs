//! LAYOUT004: a text run or interactive scene node that lies outside the scene's `safe_area` inset from the viewport edges. A scene with no `safe_area` is not judged. Off when the project has no scene files.

// frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_inputs, scene_subjects};
use crate::scene_files::{EPSILON, rect};

/// Text or an interactive target outside the safe area.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "LAYOUT004",
    slug = "content-outside-safe-area",
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
pub struct Layout004;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Layout004 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(scenes) = host.scenes() else {
            return;
        };
        for file in &scenes.files {
            let inset = file.scene.safe_area;
            if inset <= 0.0 {
                continue;
            }
            let (vw, vh) = (file.solve.viewport_width, file.solve.viewport_height);
            for node in file.solve.nodes.iter().filter(|n| file.is_content(n)) {
                let (left, top, right, bottom) = rect(node);
                if left < inset - EPSILON
                    || top < inset - EPSILON
                    || right > vw - inset + EPSILON
                    || bottom > vh - inset + EPSILON
                {
                    tracing::debug!(path = %file.path, id = %node.id, inset, "LAYOUT004: outside safe area");
                    out.fire_in(
                        &file.path,
                        file.offset_of(&node.id),
                        format!("'{}' ({left}, {top}, {right}, {bottom}) lies outside the {inset}px safe area of the {vw}x{vh} viewport", node.id),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Layout004 {
    fn subjects(&self, host: &P) -> usize {
        scene_subjects(host)
    }
}
