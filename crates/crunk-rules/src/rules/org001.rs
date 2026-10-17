//! ORG001: a stylesheet under `css_root` that sits in no declared bucket (port of `crunk/rules/_org.py` `org001`).
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::org::{buckets_model, path_ignored};
use crate::sheets::site_path;

/// A stylesheet that belongs to no `[org] buckets` directory and is not an entry sheet.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "ORG001",
    slug = "stylesheet-outside-buckets",
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
pub struct Org001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Org001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        if !buckets_model(spec) {
            return;
        }
        for stray in styles.strays.iter().filter(|p| !path_ignored(spec, p)) {
            let path = site_path(spec, stray);
            tracing::debug!(%path, "ORG001: stylesheet is in no bucket");
            out.fire_in(&path, 0, "stylesheet sits in none of the declared buckets");
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
