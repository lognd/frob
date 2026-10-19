//! LAYOUT005: an interactive scene node smaller than the WCAG 2.2 AA minimum target size of 24x24 CSS px. Off when the project has no scene files.

// frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_inputs, scene_subjects};

/// The WCAG 2.2 AA (2.5.8) minimum target size in CSS px; the Apple 44 and Android 48 minimums
/// are per-profile follow-ups.
const MIN_TARGET: f32 = 24.0;

/// An interactive target below the minimum size.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "LAYOUT005",
    slug = "target-below-minimum-size",
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
pub struct Layout005;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Layout005 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(scenes) = host.scenes() else {
            return;
        };
        for file in &scenes.files {
            for node in file
                .solve
                .nodes
                .iter()
                .filter(|n| file.is_interactive(&n.id))
            {
                if node.width < MIN_TARGET || node.height < MIN_TARGET {
                    tracing::debug!(path = %file.path, id = %node.id, "LAYOUT005: target too small");
                    out.fire_in(
                        &file.path,
                        file.offset_of(&node.id),
                        format!(
                            "interactive '{}' is {}x{} px, below the {MIN_TARGET}x{MIN_TARGET} px minimum target size",
                            node.id, node.width, node.height
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

impl<P: ?Sized + CrunkHost> Measured<P> for Layout005 {
    fn subjects(&self, host: &P) -> usize {
        scene_subjects(host)
    }
}
