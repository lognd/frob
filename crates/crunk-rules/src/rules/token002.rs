//! TOKEN002: an authored token file that does not compile (bad TOML, a malformed path or value, or two tokens
//! with one name). A broken alias is TOKEN003.

// frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8

use gob_rules::{Measured, Out, RepoRule, rule};

use crunk_tokens::dialect::DialectError;
use crunk_tokens::lint::offset_of;

use crate::host::{CrunkHost, missing_token_inputs, token_subjects};

/// An authored token file that is not valid TOML or holds a malformed token.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TOKEN002",
    slug = "token-file-invalid",
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
pub struct Token002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Token002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(tokens) = host.tokens() else {
            return;
        };
        for file in &tokens.files {
            let Err(err) = &file.set else {
                continue;
            };
            let offset = match err {
                DialectError::BrokenAlias { .. } => continue,
                DialectError::Invalid { path, .. } => offset_of(&file.text, path),
                _ => 0,
            };
            tracing::debug!(path = %file.path, %err, "TOKEN002: token file does not compile");
            out.fire_in(&file.path, offset, err.to_string());
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_token_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Token002 {
    fn subjects(&self, host: &P) -> usize {
        token_subjects(host)
    }
}
