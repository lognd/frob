//! TOKEN010: a duration token longer than the configured `[tokens] max_duration_ms` bound. Unset means no bound.

// frob:ticket 01M5XCVZBYWA5WCATMF9QYZAS8

use gob_rules::{Measured, Out, RepoRule, rule};

use crunk_tokens::lint::offset_of;

use crate::host::{CrunkHost, missing_token_inputs, token_subjects};
use crate::token_timing::over_max;

/// A duration token past the project's configured maximum.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TOKEN010",
    slug = "token-duration-too-long",
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
pub struct Token010;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Token010 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(tokens)) = (host.spec(), host.tokens()) else {
            return;
        };
        let Some(max) = spec.tokens.max_duration_ms else {
            tracing::debug!("TOKEN010: no max_duration_ms configured");
            return;
        };
        for (file, set) in tokens.ok_sets() {
            for (token, ms) in over_max(set, max) {
                tracing::debug!(path = %file.path, token = %token.name, ms, max, "TOKEN010: duration over bound");
                out.fire_in(
                    &file.path,
                    offset_of(&file.text, &token.key),
                    format!(
                        "token `{}` lasts {ms}ms, over the configured maximum of {max}ms",
                        token.name
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_token_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Token010 {
    fn subjects(&self, host: &P) -> usize {
        token_subjects(host)
    }
}
