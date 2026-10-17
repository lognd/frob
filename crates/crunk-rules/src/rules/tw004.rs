//! TW004: a colour utility (`bg-black/10`) that resolves to Tailwind's default colour, not the project theme.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use crunk_spec::naming;
use crunk_tailwind::defaults::{V3_COLOR_HEXES, V3_COLOR_NAMES};
use crunk_values::Color;
use gob_rules::{Out, RepoRule, rule};

use crate::color::Palette;
use crate::host::{CrunkHost, missing_inputs};
use crate::mode::Mode;
use crate::tailwind::{sites, split_alpha, split_word_key, theme_view};

/// A `word-colorpart` utility naming a Tailwind default colour the theme does not define.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW004",
    slug = "tailwind-default-color",
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
pub struct Tw004;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tw004 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let view = theme_view(host, spec);
        let palette = Palette::new(Mode::DEFAULT.palette(spec));
        for site in sites(spec, styles) {
            let (stem, _) = split_alpha(site.name);
            let Some((_, part)) = split_word_key(stem) else {
                continue;
            };
            if !V3_COLOR_NAMES.contains(&part) || view.map.contains_key(part) {
                continue;
            }
            let nearest = V3_COLOR_HEXES
                .iter()
                .find(|(n, _)| *n == part)
                .and_then(|(_, hex)| Color::parse(hex).ok())
                .and_then(|c| palette.nearest(c))
                .map_or_else(String::new, |(n, d)| {
                    format!(
                        "; nearest is {} (distance {d:.2})",
                        naming::color_token(&spec.tokens, n)
                    )
                });
            tracing::debug!(path = %site.path, utility = site.name, "TW004: default colour used");
            out.fire_in(
                &site.path,
                site.offset,
                format!(
                    "utility '{}' resolves to Tailwind's default color '{part}', not the project theme{nearest}",
                    site.name
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
