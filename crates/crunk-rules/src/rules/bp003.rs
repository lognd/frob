//! BP003: a `max-width` media query in a mobile-first project.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::org::line_offset;
use crate::sheets::site_path;

/// A `max-width` media query: breakpoints are mobile-first, so styles are layered up with `min-width`.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "BP003",
    slug = "max-width-media-query",
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
pub struct Bp003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Bp003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            for query in sheet.media_queries.iter().filter(|q| q.max_px.is_some()) {
                tracing::debug!(%path, prelude = %query.prelude, "BP003: max-width query");
                out.fire_in(
                    &path,
                    line_offset(&sheet.source, query.line),
                    format!(
                        "media query `{}` is desktop-first; write mobile-first `min-width` queries",
                        query.prelude
                    ),
                );
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
