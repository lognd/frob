//! TOKENS001: a generated token file (the CSS file, the Tailwind theme mapping, the JSON export)
//! that is missing or differs from what the spec renders now (the drift check of the Python
//! shell). The files are compared as side input; the CSS file byte for byte, the JSON ones after
//! parsing. A banner-only difference keeps the rule's severity but says so.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::tokens_drift;

/// A generated token file that is missing or has drifted from the spec.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TOKENS001",
    slug = "tokens-file-drift",
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
pub struct Tokens001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tokens001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(spec) = host.spec() else {
            return;
        };
        match tokens_drift::check(spec) {
            Ok(found) => {
                for item in found {
                    tracing::debug!(path = %item.path, "TOKENS001: drifted token file");
                    out.fire_in(&item.path, 0, item.message);
                }
            }
            Err(err) => {
                tracing::warn!(%err, "TOKENS001: drift cannot be decided");
                out.unresolved(format!("the token files cannot be compared: {err}"));
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Tokens001 {
    fn subjects(&self, host: &P) -> usize {
        usize::from(host.spec().is_some())
    }
}
