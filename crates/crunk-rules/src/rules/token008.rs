//! TOKEN008: duplicate values under different names: colours within `[lint] color_tolerance` of each other
//! and identical dimensions or durations. Aliases repeat their target on purpose and are skipped.

// frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8

use gob_rules::{Measured, Out, RepoRule, rule};

use crunk_tokens::lint::{near_duplicates, offset_of};

use crate::host::{CrunkHost, missing_token_inputs, token_subjects};

/// Two tokens under different names holding the same or a near-identical value.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TOKEN008",
    slug = "token-near-duplicate",
    severity = Warn,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Token008;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Token008 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(tokens)) = (host.spec(), host.tokens()) else {
            return;
        };
        for (file, set) in tokens.ok_sets() {
            for (a, b) in near_duplicates(set, spec.lint.color_tolerance) {
                tracing::debug!(path = %file.path, a = %a.name, b = %b.name, "TOKEN008: near duplicate");
                out.fire_in(
                    &file.path,
                    offset_of(&file.text, &b.key),
                    format!(
                        "token `{}` repeats the value of `{}`; alias one to the other or drop it",
                        b.name, a.name
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_token_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Token008 {
    fn subjects(&self, host: &P) -> usize {
        token_subjects(host)
    }
}
