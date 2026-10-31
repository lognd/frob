//! LAYOUT002: two sibling scene nodes whose solved rectangles overlap with positive area (content collision). Off when the project has no scene files.

// frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_inputs, scene_subjects};
use crate::scene_files::{EPSILON, rect};

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
        let Some(scenes) = host.scenes() else {
            return;
        };
        for file in &scenes.files {
            for (i, a) in file.solve.nodes.iter().enumerate() {
                for b in &file.solve.nodes[i + 1..] {
                    if a.parent.is_none() || a.parent != b.parent {
                        continue;
                    }
                    let (al, at, ar, ab) = rect(a);
                    let (bl, bt, br, bb) = rect(b);
                    let across = ar.min(br) - al.max(bl);
                    let down = ab.min(bb) - at.max(bt);
                    if across > EPSILON && down > EPSILON {
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
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Layout002 {
    fn subjects(&self, host: &P) -> usize {
        scene_subjects(host)
    }
}
