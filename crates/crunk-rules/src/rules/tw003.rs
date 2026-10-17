//! TW003: an alpha-modified colour utility (`bg-brand/50`) whose theme mapping cannot take alpha.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use crunk_tailwind::runtime::TailwindVersion;
use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::tailwind::{sites, split_alpha, split_word_key, theme_view};

/// An `x-key/NN` utility whose `tw_theme` entry has no `<alpha-value>` placeholder.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW003",
    slug = "tailwind-alpha-no-placeholder",
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
        let (Some(spec), Some(styles), Some(theme)) =
            (host.spec(), host.styles(), host.tailwind_theme())
        else {
            return;
        };
        if theme.version == TailwindVersion::V4 {
            tracing::debug!("TW003: Tailwind v4 applies alpha natively; skipped");
            return;
        }
        let view = theme_view(host, spec);
        for site in sites(spec, styles) {
            let (stem, Some(_)) = split_alpha(site.name) else {
                continue;
            };
            let Some((_, key)) = split_word_key(stem) else {
                continue;
            };
            let Some(mapping) = view.map.get(key) else {
                continue;
            };
            if mapping.contains("<alpha-value>") {
                continue;
            }
            tracing::debug!(path = %site.path, utility = site.name, "TW003: alpha modifier is a no-op");
            out.fire_in(
                &site.path,
                site.offset,
                format!(
                    "utility '{}' applies an alpha modifier but tw_theme entry '{key}' maps to '{mapping}', which has no <alpha-value> placeholder -- the modifier is a silent no-op",
                    site.name
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host).or_else(|| {
            host.tailwind_theme()
                .is_none()
                .then(|| "no [tailwind] theme ingested".to_owned())
        })
    }
}
