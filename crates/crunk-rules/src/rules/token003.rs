//! TOKEN003: an alias that names no token in its file, or whose chain loops back on itself (in the default
//! value or in a mode). Each token file is self-contained, so an alias never reaches another file.

// frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8

use gob_rules::{Measured, Out, RepoRule, rule};

use crunk_tokens::dialect::DialectError;

use crate::host::{CrunkHost, missing_token_inputs, token_subjects};

/// A token alias that names no token or whose chain is a cycle.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TOKEN003",
    slug = "token-alias-broken",
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
pub struct Token003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Token003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(tokens) = host.tokens() else {
            return;
        };
        for file in &tokens.files {
            let Err(err @ DialectError::BrokenAlias { .. }) = &file.set else {
                continue;
            };
            tracing::debug!(path = %file.path, %err, "TOKEN003: alias does not resolve");
            out.fire_in(&file.path, 0, err.to_string());
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_token_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Token003 {
    fn subjects(&self, host: &P) -> usize {
        token_subjects(host)
    }
}
