//! TW005: a class name built at runtime, which Tailwind and crunk cannot see.
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::org::line_offset;
use crate::sheets::{is_tokens_sheet, site_path};

/// A `className` site with a part that is not statically known.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW005",
    slug = "tailwind-dynamic-class",
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
        for sheet in styles.sheets.iter().filter(|s| !is_tokens_sheet(s)) {
            let path = site_path(spec, &sheet.path);
            for site in &sheet.dynamic_classes {
                tracing::debug!(%path, line = site.line, "TW005: class name is built at runtime");
                out.fire_in(
                    &path,
                    line_offset(&sheet.source, site.line),
                    "class name is built at runtime; Tailwind cannot generate it and crunk cannot judge it"
                        .to_owned(),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
