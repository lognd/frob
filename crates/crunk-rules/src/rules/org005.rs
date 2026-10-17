//! ORG005: a stylesheet outside `css_root` that no `[org] ignore` glob covers (port of `crunk/rules/_org.py` `org005`).
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;

/// A `.css` file the organization rules do not govern because it sits outside `css_root`.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "ORG005",
    slug = "ungoverned-stylesheet",
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
pub struct Org005;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Org005 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        for file in &styles.ungoverned {
            let path = site_path(spec, file);
            tracing::debug!(%path, "ORG005: stylesheet is ungoverned");
            out.fire_in(
                &path,
                0,
                "stylesheet is outside css_root and not ignored by [org] ignore",
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
