//! BP001: a media query width that is not a declared breakpoint.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Out, RepoRule, rule};

use crate::breakpoints::matches_breakpoint;
use crate::host::{CrunkHost, missing_inputs};
use crate::org::line_offset;
use crate::sheets::site_path;

/// A `min-width` or `max-width` media query whose px width is not in `[breakpoints]`.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "BP001",
    slug = "media-query-off-breakpoint",
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
pub struct Bp001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Bp001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let mut declared: Vec<i64> = spec.breakpoints.points.values().copied().collect();
        declared.sort_unstable();
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            for query in &sheet.media_queries {
                for px in [query.min_px, query.max_px].into_iter().flatten() {
                    if matches_breakpoint(px, spec) {
                        continue;
                    }
                    tracing::debug!(%path, prelude = %query.prelude, px, "BP001: width is not a breakpoint");
                    out.fire_in(
                        &path,
                        line_offset(&sheet.source, query.line),
                        format!(
                            "media query '{}' uses {px}px, which is not a declared breakpoint {declared:?}",
                            query.prelude
                        ),
                    );
                }
            }
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
