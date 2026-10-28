//! TOKEN009: a deprecated token (`deprecated = "reason"`) that another token aliases or a stylesheet reads
//! through `var()`. The deprecated token's own definition is not a use.

// frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8

use gob_rules::{Measured, Out, RepoRule, rule};

use std::collections::BTreeSet;

use crunk_tokens::lint::{alias_edges, offset_of};

use crate::host::{CrunkHost, missing_token_inputs, token_subjects};
use crate::sheets::{is_tokens_sheet, site_path};

/// A deprecated token that is still aliased or read.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TOKEN009",
    slug = "token-deprecated-used",
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
pub struct Token009;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Token009 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(tokens)) = (host.spec(), host.tokens()) else {
            return;
        };
        let reasons: std::collections::BTreeMap<&str, &str> = tokens
            .ok_sets()
            .flat_map(|(_, set)| set.iter())
            .filter_map(|t| t.deprecated.as_deref().map(|why| (t.name.as_str(), why)))
            .collect();
        for (file, set) in tokens.ok_sets() {
            let mut seen = BTreeSet::new();
            for (from, to) in alias_edges(set) {
                let Some(why) = reasons.get(to) else {
                    continue;
                };
                if !seen.insert((from.name.as_str(), to)) {
                    continue;
                }
                tracing::debug!(path = %file.path, token = %from.name, target = to, "TOKEN009: alias of a deprecated token");
                out.fire_in(
                    &file.path,
                    offset_of(&file.text, &from.key),
                    format!("token `{}` aliases deprecated `{to}`: {why}", from.name),
                );
            }
        }
        let Some(styles) = host.styles() else {
            return;
        };
        for sheet in styles.sheets.iter().filter(|s| !is_tokens_sheet(s)) {
            let path = site_path(spec, &sheet.path);
            for var in sheet.declarations.iter().flat_map(|d| &d.var_refs) {
                if let Some(why) = reasons.get(var.name.as_str()) {
                    tracing::debug!(%path, token = %var.name, "TOKEN009: deprecated token read");
                    out.fire_in(
                        &path,
                        var.span.0,
                        format!("`var({})` reads a deprecated token: {why}", var.name),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_token_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Token009 {
    fn subjects(&self, host: &P) -> usize {
        token_subjects(host)
    }
}
