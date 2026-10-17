//! TW002: an arbitrary Tailwind colour (`bg-[#123456]`) that is not a palette colour.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Out, RepoRule, rule};

use crate::color::Palette;
use crate::host::{CrunkHost, missing_inputs};
use crate::mode::modes;
use crate::tailwind::{Arbitrary, arbitrary, sites};

/// An arbitrary-value colour utility whose colour is not a palette colour.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW002",
    slug = "tailwind-arbitrary-color-off-palette",
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
pub struct Tw002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tw002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let root = spec.project.root_font_size;
        let sites = sites(spec, styles);
        for mode in modes(spec) {
            let palette = Palette::new(mode.palette(spec));
            for site in &sites {
                let Some(Arbitrary::Color(color)) = arbitrary(&site.candidate, root) else {
                    continue;
                };
                if palette.conforms(color) {
                    continue;
                }
                let nearest = palette
                    .nearest(color)
                    .map_or_else(String::new, |(name, d)| {
                        format!("; nearest is `{name}` (distance {d:.2})")
                    });
                tracing::debug!(path = %site.path, class = %site.candidate.raw, "TW002: colour is off the palette");
                out.fire_in(
                    &site.path,
                    site.offset,
                    format!(
                        "`{}` uses {}, which is not a palette color{nearest}{}",
                        site.candidate.raw,
                        color.to_hex(),
                        mode.suffix()
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
