//! RESP001: a declared breakpoint that no scene file solves at (breakpoint coverage): every `[breakpoints]` width needs a scene whose viewport is that wide. Off when no breakpoints are declared or the project has no scene files.

// frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_scene_inputs, scene_subjects};

/// A declared breakpoint with no scene at its width.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "RESP001",
    slug = "breakpoint-without-scene",
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
        let (Some(spec), Some(scenes)) = (host.spec(), host.scenes()) else {
            return;
        };
        for (name, &bp) in &spec.breakpoints.points {
            #[allow(clippy::cast_precision_loss, reason = "breakpoints are small integers")]
            let width = bp as f32;
            if scenes
                .files
                .iter()
                .any(|f| (f.solve.viewport_width - width).abs() < f32::EPSILON)
            {
                continue;
            }
            tracing::debug!(name, bp, "RESP001: no scene at breakpoint");
            out.fire_in(
                "crunk.toml",
                0,
                format!("breakpoint '{name}' ({bp}px) has no scene solved at that viewport width"),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_inputs(host).or_else(|| {
            host.spec()
                .is_some_and(|s| s.breakpoints.points.is_empty())
                .then(|| "no [breakpoints] declared".to_owned())
        })
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Resp001 {
    fn subjects(&self, host: &P) -> usize {
        scene_subjects(host)
    }
}
