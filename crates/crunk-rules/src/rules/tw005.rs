//! TW005: a named utility (`p-5`) that falls through to Tailwind's default scale, bypassing the declared one.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::tailwind::{
    default_scale, numeric_key, sites, split_alpha, split_arbitrary, split_family_stem, theme_view,
};

/// A `family-key` utility whose key is in Tailwind's default scale and not in the project theme.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW005",
    slug = "tailwind-default-scale",
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
pub struct Tw005;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tw005 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let view = theme_view(host, spec);
        for site in sites(spec, styles) {
            let (stem, _) = split_alpha(site.name);
            if split_arbitrary(stem).is_some() {
                continue;
            }
            let Some((family, key)) = split_family_stem(stem) else {
                continue;
            };
            let Some(scale) = default_scale(family) else {
                continue;
            };
            if matches!(family, "z" | "-z") && spec.layers.is_empty() {
                continue;
            }
            if family == "text" && !numeric_key(key) {
                continue;
            }
            if !scale.keys.contains(&key) || view.map.contains_key(key) {
                continue;
            }
            tracing::debug!(path = %site.path, utility = site.name, "TW005: default scale used");
            out.fire_in(
                &site.path,
                site.offset,
                format!(
                    "utility '{}' resolves to Tailwind's default {} scale (key '{key}'), bypassing the declared {} scale",
                    site.name, scale.name, scale.name
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
