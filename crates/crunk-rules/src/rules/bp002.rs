//! BP002: a responsive utility of a layout-critical family with no unprefixed base.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Out, RepoRule, rule};

use crate::breakpoints::{base_family, responsive_variant, same_family};
use crate::host::{CrunkHost, missing_inputs};
use crate::tailwind::sites;

/// A breakpoint-prefixed utility of a `base_required` family (`md:flex`) with no unprefixed utility of that family on its line.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "BP002",
    slug = "responsive-without-base",
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
pub struct Bp002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Bp002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let required = &spec.breakpoints.base_required;
        let sites = sites(spec, styles);
        for site in &sites {
            let Some(point) = responsive_variant(site.variants, spec) else {
                continue;
            };
            let name = &site.candidate.raw;
            let Some(family) = base_family(&site.candidate.utility, required) else {
                continue;
            };
            let has_base = sites.iter().any(|other| {
                other.path == site.path
                    && other.line == site.line
                    && other.variants.is_empty()
                    && base_family(&other.candidate.utility, required)
                        .is_some_and(|f| same_family(f, family))
            });
            if has_base {
                continue;
            }
            tracing::debug!(path = %site.path, class = %name, "BP002: responsive utility has no mobile base");
            out.fire_in(
                &site.path,
                site.offset,
                format!(
                    "`{point}:{name}` has no unprefixed `{family}` base for the smallest viewport"
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host).or_else(|| {
            host.spec()
                .is_some_and(|s| s.breakpoints.points.is_empty())
                .then(|| "no [breakpoints] declared".to_owned())
        })
    }
}
