//! TOKEN005: the naming and layering convention: kebab-case path segments, a tier prefix that matches the
//! token's tier, and no component token aliasing a primitive directly (skipping the semantic layer).

// frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8

use gob_rules::{Measured, Out, RepoRule, rule};

use crunk_tokens::lint::{naming_issues, offset_of, tier_skips};

use crate::host::{CrunkHost, missing_token_inputs, token_subjects};

/// A token whose path breaks the naming or layering convention.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TOKEN005",
    slug = "token-naming",
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
pub struct Token005;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Token005 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(tokens) = host.tokens() else {
            return;
        };
        for (file, set) in tokens.ok_sets() {
            for (token, why) in naming_issues(set) {
                tracing::debug!(path = %file.path, token = %token.name, %why, "TOKEN005: naming issue");
                out.fire_in(
                    &file.path,
                    offset_of(&file.text, &token.key),
                    format!("token `{}`: {why}", token.name),
                );
            }
            for (from, to) in tier_skips(set) {
                tracing::debug!(path = %file.path, token = %from.name, target = %to.name, "TOKEN005: tier skip");
                out.fire_in(
                    &file.path,
                    offset_of(&file.text, &from.key),
                    format!(
                        "component token `{}` aliases primitive `{}` directly; alias a semantic token instead",
                        from.name, to.name
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_token_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Token005 {
    fn subjects(&self, host: &P) -> usize {
        token_subjects(host)
    }
}
