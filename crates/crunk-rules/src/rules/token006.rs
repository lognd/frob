//! TOKEN006: mode completeness: a token that overrides one mode must override every mode its file declares,
//! or the missing mode silently falls back to the default value.

// frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8

use gob_rules::{Measured, Out, RepoRule, rule};

use crunk_tokens::lint::{mode_gaps, offset_of};

use crate::host::{CrunkHost, missing_token_inputs, token_subjects};

/// A token that overrides some declared mode but not all of them.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TOKEN006",
    slug = "token-mode-incomplete",
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
pub struct Token006;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Token006 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(tokens) = host.tokens() else {
            return;
        };
        for (file, set) in tokens.ok_sets() {
            for (token, missing) in mode_gaps(set) {
                tracing::debug!(path = %file.path, token = %token.name, ?missing, "TOKEN006: mode gap");
                out.fire_in(
                    &file.path,
                    offset_of(&file.text, &token.key),
                    format!(
                        "token `{}` has no value in mode(s) {}",
                        token.name,
                        missing.join(", ")
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_token_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Token006 {
    fn subjects(&self, host: &P) -> usize {
        token_subjects(host)
    }
}
