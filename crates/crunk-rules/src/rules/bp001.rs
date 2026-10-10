//! BP001: a recorded `@media` `min-width` or `max-width` px value that matches no declared
//! breakpoint (port of `crunk/rules/_breakpoints.py` `bp001`). The `-0.02px` idiom is accepted;
//! a query with neither value parsed is exempt. Off when no breakpoints are declared.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::breakpoints::matches_breakpoint;
use crate::host::CrunkHost;
use crate::sheets::{examined_sheets, line_offset, site_path};

/// A media query width that is not a declared breakpoint.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "BP001",
    slug = "media-query-off-breakpoints",
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
pub struct Bp001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Bp001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let points = &spec.breakpoints.points;
        let mut declared: Vec<i64> = points.values().copied().collect();
        declared.sort_unstable();
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            for query in &sheet.media_queries {
                for px in [query.min_px, query.max_px].into_iter().flatten() {
                    if matches_breakpoint(px, points) {
                        continue;
                    }
                    tracing::debug!(%path, line = query.line, px, "BP001: undeclared breakpoint");
                    out.fire_in(
                        &path,
                        line_offset(&sheet.source, query.line),
                        format!(
                            "media query '{}' uses {px:?}px, which is not a declared breakpoint {declared:?}",
                            query.prelude
                        ),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        crate::breakpoints::off_reason(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Bp001 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
