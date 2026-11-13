//! STATE004: a screen state with no render-ledger entry on a platform it applies to. Off when the project declares no screen state or the pipeline gathered no render ledger.

// frob:ticket 01M5EF4A7DQJQ2SHXYAYCAB73X

use gob_rules::{Out, RepoRule, rule};

use crate::host::CrunkHost;

/// A screen state that has no render on one of its platforms.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "STATE004",
    slug = "render-missing",
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
pub struct State004;

impl<P: ?Sized + CrunkHost> RepoRule<P> for State004 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(ledger)) = (host.spec(), host.renders()) else {
            return;
        };
        if let Some(why) = &ledger.unreadable {
            tracing::warn!(%why, "STATE004: render ledger cannot be judged");
            out.unresolved_in(
                "crunk.toml",
                0,
                format!("render coverage cannot be judged: {why}"),
            );
            return;
        }
        for (screen, state, platform) in spec.cell_triples() {
            if ledger.has(&screen, &state, &platform) {
                continue;
            }
            tracing::debug!(%screen, %state, %platform, "STATE004: render missing");
            out.fire_in(
                "crunk.toml",
                0,
                format!(
                    "screen '{screen}' state '{state}' has no render for platform '{platform}'; run the gallery render"
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        if host.spec().is_none() {
            return Some("no valid crunk.toml".to_owned());
        }
        if host.renders().is_none() {
            return Some("no render ledger was gathered".to_owned());
        }
        None
    }
}
