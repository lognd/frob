//! ORG005: a `.css` file outside `css_root` that no `[org] ignore` glob covers (port of
//! `crunk/rules/_org.py` `org005`, r4/CR-11): the ungoverned scan's paths, one finding each.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::{examined_sheets, site_path};

/// A stylesheet that lives outside the managed CSS root.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "ORG005",
    slug = "ungoverned-stylesheet",
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
pub struct Org005;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Org005 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let css_root = site_path(spec, &spec.css_root());
        for ungoverned in &styles.ungoverned {
            let path = site_path(spec, ungoverned);
            tracing::debug!(%path, "ORG005: ungoverned stylesheet");
            out.fire_in(
                &path,
                0,
                format!(
                    "{path} is a CSS file outside {css_root} (css_root); add a matching glob to [org].ignore to exempt it"
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Org005 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, |styles| {
            examined_sheets(styles) + styles.ungoverned.len()
        })
    }
}
