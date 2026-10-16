//! TOKEN007: a scope violation: a stylesheet binds `var(--token)` to a property whose scope the token does
//! not declare (a `scopes = ["spacing"]` token read by `color`). Tokens without scopes are free.

// frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8

use gob_rules::{Measured, Out, RepoRule, rule};

use std::collections::BTreeMap;

use crunk_tokens::Token;
use crunk_tokens::lint::{allows_scope, scope_of_property};

use crate::host::{CrunkHost, missing_token_style_inputs, token_subjects};
use crate::sheets::{is_tokens_sheet, site_path};

/// A token bound to a CSS property outside its declared scopes.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TOKEN007",
    slug = "token-scope-violation",
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
pub struct Token007;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Token007 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(tokens), Some(styles)) = (host.spec(), host.tokens(), host.styles())
        else {
            return;
        };
        let by_name: BTreeMap<&str, &Token> = tokens
            .ok_sets()
            .flat_map(|(_, set)| set.iter())
            .map(|t| (t.name.as_str(), t))
            .collect();
        for sheet in styles.sheets.iter().filter(|s| !is_tokens_sheet(s)) {
            let path = site_path(spec, &sheet.path);
            for decl in &sheet.declarations {
                let Some(scope) = scope_of_property(&decl.prop) else {
                    continue;
                };
                for var in &decl.var_refs {
                    let Some(token) = by_name.get(var.name.as_str()) else {
                        continue;
                    };
                    if allows_scope(token, scope) {
                        continue;
                    }
                    tracing::debug!(%path, token = %token.name, prop = %decl.prop, "TOKEN007: scope violation");
                    out.fire_in(
                        &path,
                        var.span.0,
                        format!(
                            "token `{}` is not scoped for `{}` ({scope:?})",
                            token.name, decl.prop
                        ),
                    );
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_token_style_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Token007 {
    fn subjects(&self, host: &P) -> usize {
        token_subjects(host)
    }
}
