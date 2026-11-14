//! RESP001: a scene whose root is wider than the viewport at a declared breakpoint (responsive overflow), read from the crunk-layout solve of each `design/scenes/*.scene.html` at every `[breakpoints]` width. Off when no breakpoints are declared or the project has no scene files.

// frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62
// frob:ticket 01M6Z2SXMWBKP1SS1NPE0MT1GQ

use gob_rules::{Measured, Out, RepoRule, rule};

use crunk_layout::findings::{rect, roots_wider_than_viewport};

use crate::host::{CrunkHost, missing_scene_doc_inputs, scene_doc_subjects};
use crate::scene_docs::{SOLVE_VIEWPORT, SceneDocFile};

/// A scene root wider than the viewport at a declared breakpoint.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "RESP001",
    slug = "root-wider-than-breakpoint",
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
pub struct Resp001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Resp001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(facts)) = (host.spec(), host.scene_docs()) else {
            return;
        };
        for (name, &bp) in &spec.breakpoints.points {
            #[allow(clippy::cast_precision_loss, reason = "breakpoints are small integers")]
            let viewport = (bp as f32, SOLVE_VIEWPORT.1);
            for file in &facts.files {
                let solve = match file.solve_at(viewport) {
                    Ok(solve) => solve,
                    Err(why) => {
                        tracing::warn!(path = %file.path, name, %why, "RESP001: scene does not solve");
                        out.unresolved_in(&file.path, 0, SceneDocFile::unsolved_message(&why));
                        continue;
                    }
                };
                for root in roots_wider_than_viewport(&solve) {
                    let (_, _, right, _) = rect(root);
                    tracing::debug!(path = %file.path, name, bp, id = %root.id, "RESP001: root wider than viewport");
                    out.fire_in(
                        &file.path,
                        file.offset_of(&root.id),
                        format!(
                            "root '{}' is {right}px wide, wider than the '{name}' breakpoint ({bp}px)",
                            root.id
                        ),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host).or_else(|| {
            host.spec()
                .is_some_and(|s| s.breakpoints.points.is_empty())
                .then(|| "no [breakpoints] declared".to_owned())
        })
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Resp001 {
    fn subjects(&self, host: &P) -> usize {
        scene_doc_subjects(host)
    }
}
