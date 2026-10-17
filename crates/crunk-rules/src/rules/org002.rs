//! ORG002: a class name not written in the configured `class_case` (port of `crunk/rules/_org.py` `org002`).
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::org::{is_ignored, line_offset, matches_case};
use crate::sheets::{is_tokens_sheet, site_path};

/// A class selector whose name is not in the casing `[org] class_case` requires.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "ORG002",
    slug = "class-case",
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
pub struct Org002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Org002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let case = spec.org.class_case;
        for sheet in styles
            .sheets
            .iter()
            .filter(|s| !is_tokens_sheet(s) && !is_ignored(spec, s))
        {
            let path = site_path(spec, &sheet.path);
            for class in &sheet.class_selectors {
                if !matches_case(&class.name, case) {
                    tracing::debug!(%path, class = %class.name, "ORG002: class is not in the required case");
                    out.fire_in(
                        &path,
                        line_offset(&sheet.source, class.line),
                        format!("class `{}` is not {case:?}-case", class.name),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
