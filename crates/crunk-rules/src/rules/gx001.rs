//! GX001: a `[game]` profile that has not declared every accessibility coverage key (volume
//! channels, haptics toggle, time limits, subtitle format, text in images, glyph icons). Off when
//! the project has no `[game]` table.

// frob:ticket 01M4D95WWXAWJF1M9ST8RX5YZG

use gob_rules::{Out, RepoRule, rule};

use crate::host::CrunkHost;

/// A game profile missing a declared accessibility coverage key.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "GX001",
    slug = "game-coverage-undeclared",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Gx001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Gx001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(game) = host.spec().and_then(|s| s.game.as_ref()) else {
            return;
        };
        for (key, guideline) in game.missing() {
            tracing::debug!(key, "GX001: coverage key not declared");
            out.fire_in(
                "crunk.toml",
                0,
                format!("[game] coverage lacks `{key}`: {guideline}"),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        host.spec()
            .is_none_or(|s| s.game.is_none())
            .then(|| "no [game] profile declared".to_owned())
    }
}
