//! STATE005: two states of one screen render too alike on a platform. Off when the project declares no screen state or the pipeline gathered no render ledger.

// frob:ticket 01M5EF4A9VM42NW2805KJJ86Q4

use gob_rules::{Out, RepoRule, rule};

use crate::host::CrunkHost;
use crate::render_ledger::{MIN_STATE_DIFF_PPM, ledger_inapplicable};

/// Two states of a screen whose renders differ by less than the threshold.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "STATE005",
    slug = "state-diff-low",
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
pub struct State005;

impl<P: ?Sized + CrunkHost> RepoRule<P> for State005 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(_), Some(ledger)) = (host.spec(), host.renders()) else {
            return;
        };
        if let Some(why) = &ledger.unreadable {
            tracing::warn!(%why, "STATE005: render ledger cannot be judged");
            out.unresolved_in(
                "crunk.toml",
                0,
                format!("state differences cannot be judged: {why}"),
            );
            return;
        }
        for d in &ledger.diffs {
            if d.diff_ppm >= MIN_STATE_DIFF_PPM {
                continue;
            }
            tracing::debug!(screen = %d.screen, platform = %d.platform, a = %d.a, b = %d.b, diff_ppm = d.diff_ppm, "STATE005: states render too alike");
            out.fire_in(
                "crunk.toml",
                0,
                format!(
                    "screen '{}' states '{}' and '{}' differ by {} ppm on platform '{}', under the {MIN_STATE_DIFF_PPM} ppm minimum; make the states visibly distinct",
                    d.screen, d.a, d.b, d.diff_ppm, d.platform
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        ledger_inapplicable(host)
    }
}
