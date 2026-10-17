//! TW001: an arbitrary Tailwind length (`p-[13px]`) that is not a step of its scale.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::tailwind::{Arbitrary, arbitrary, on_scale, sites};

/// An arbitrary-value utility whose px length is not on the `[scales]` list its root takes.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW001",
    slug = "tailwind-arbitrary-off-scale",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Tw001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tw001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let root = spec.project.root_font_size;
        for site in sites(spec, styles) {
            let Some(Arbitrary::Length { kind, px }) = arbitrary(&site.candidate, root) else {
                continue;
            };
            if on_scale(px, kind.steps(spec)) {
                continue;
            }
            tracing::debug!(path = %site.path, class = %site.candidate.raw, px, "TW001: length is off the scale");
            out.fire_in(
                &site.path,
                site.offset,
                format!(
                    "`{}` uses {px}px, which is not on the {} scale",
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
