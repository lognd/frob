//! ORG004: a custom property defined outside the tokens file (port of `crunk/rules/_org.py`
//! `org004`). Honours `[org] tokens_only_custom_props = false`, which turns the rule off.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use crunk_ingest::Bucket;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::{examined_sheets, line_offset, site_path};

/// A `--x:` definition in a stylesheet other than the generated tokens file.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "ORG004",
    slug = "custom-property-outside-tokens",
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
pub struct Org004;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Org004 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        for sheet in styles
            .sheets
            .iter()
            .filter(|s| s.bucket != Some(Bucket::Tokens))
        {
            let path = site_path(spec, &sheet.path);
            for prop in &sheet.custom_props {
                tracing::debug!(%path, line = prop.line, name = %prop.name, "ORG004: custom property");
                out.fire_in(
                    &path,
                    line_offset(&sheet.source, prop.line),
                    format!(
                        "custom property '{}' defined outside the tokens file",
                        prop.name
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        if let Some(why) = missing_inputs(host) {
            return Some(why);
        }
        host.spec()
            .is_some_and(|spec| !spec.org.tokens_only_custom_props)
            .then(|| "[org] tokens_only_custom_props is off".to_owned())
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Org004 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
