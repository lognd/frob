//! ORG004: a custom property defined outside the generated tokens file (port of `crunk/rules/_org.py` `org004`).
//!
//! Ships as a Rust rule ahead of the GRL executor (D76 allows recorded tier-0 exceptions); the
//! std-pack ticket replaces it.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use gob_rules::{Out, RepoRule, rule};

use crunk_ingest::Bucket;

use crate::host::{CrunkHost, missing_inputs};
use crate::org::{is_ignored, line_offset};
use crate::sheets::site_path;

/// A `--x:` definition in a stylesheet other than the tokens file.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "ORG004",
    slug = "custom-prop-outside-tokens",
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
pub struct Org004;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Org004 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        if !spec.org.tokens_only_custom_props {
            return;
        }
        for sheet in styles
            .sheets
            .iter()
            .filter(|s| s.bucket != Some(Bucket::Tokens) && !is_ignored(spec, s))
        {
            let path = site_path(spec, &sheet.path);
            for prop in &sheet.custom_props {
                tracing::debug!(%path, name = %prop.name, "ORG004: custom property outside the tokens file");
                out.fire_in(
                    &path,
                    line_offset(&sheet.source, prop.line),
                    format!(
                        "custom property {} is defined outside the tokens file",
                        prop.name
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}
