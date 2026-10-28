//! TOKEN004: a token nothing refers to: no `var(--name)` in an examined stylesheet and no alias from another
//! token. The generated tokens sheet does not count as a use.

// frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8

use gob_rules::{Measured, Out, RepoRule, rule};

use crunk_tokens::lint::{offset_of, unused};

use crate::host::{CrunkHost, missing_token_style_inputs, token_subjects};
use crate::token_files::used_vars;

/// A token that no stylesheet and no other token refers to.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TOKEN004",
    slug = "token-unused",
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
pub struct Token004;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Token004 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(tokens), Some(styles)) = (host.tokens(), host.styles()) else {
            return;
        };
        let used = used_vars(styles);
        for (file, set) in tokens.ok_sets() {
            for token in unused(set, &used) {
                tracing::debug!(path = %file.path, token = %token.name, "TOKEN004: unused token");
                out.fire_in(
                    &file.path,
                    offset_of(&file.text, &token.key),
                    format!(
                        "token `{}` is never read by a stylesheet or aliased by another token",
                        token.name
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_token_style_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Token004 {
    fn subjects(&self, host: &P) -> usize {
        token_subjects(host)
    }
}
