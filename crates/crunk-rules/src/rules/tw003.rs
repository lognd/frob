//! TW003: an arbitrary Tailwind length that is on its scale, so a named utility exists.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::tailwind::{Arbitrary, arbitrary, on_scale, sites};

/// An arbitrary-value utility (`p-[16px]`) whose length is a scale step: write the scale utility.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW003",
    slug = "tailwind-arbitrary-on-scale",
    severity = Warn,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Tw003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tw003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let root = spec.project.root_font_size;
        for site in sites(spec, styles) {
            let Some(Arbitrary::Length { kind, px }) = arbitrary(&site.candidate, root) else {
                continue;
            };
            if !on_scale(px, kind.steps(spec)) {
                continue;
            }
            tracing::debug!(path = %site.path, class = %site.candidate.raw, px, "TW003: arbitrary length is a scale step");
            out.fire_in(
                &site.path,
                site.offset,
                format!(
                    "`{}` is {px}px, a step of the {} scale; use the scale utility",
                    site.candidate.raw,
                    kind.name()
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
