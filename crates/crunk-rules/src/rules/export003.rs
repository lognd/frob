//! EXPORT003: Figma plan limits. The Figma variables export (collections are tiers, modes are
//! modes, variables are tokens) must fit the modes and variables per collection the `[figma]`
//! plan allows, or the import into Figma fails.

// frob:ticket 01M5XCVZFESE41V1GVEYC5VP5X

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::export_figma::plan_findings;
use crate::host::{CrunkHost, missing_inputs};

/// A Figma collection with more modes or variables than the configured plan allows.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "EXPORT003",
    slug = "figma-plan-limit",
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
pub struct Export003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Export003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(spec) = host.spec() else {
            return;
        };
        match plan_findings(spec) {
            Ok(found) => {
                for message in found {
                    tracing::debug!(%message, "EXPORT003: plan limit exceeded");
                    out.fire_in("crunk.toml", 0, message);
                }
            }
            Err(err) => {
                tracing::warn!(%err, "EXPORT003: the token set cannot be built");
                out.unresolved(format!("the Figma export cannot be sized: {err}"));
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host).or_else(|| {
            host.spec()
                .is_some_and(|s| s.figma.is_none())
                .then(|| "no [figma] plan is configured".to_owned())
        })
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Export003 {
    fn subjects(&self, host: &P) -> usize {
        usize::from(host.spec().is_some_and(|s| s.figma.is_some()))
    }
}
