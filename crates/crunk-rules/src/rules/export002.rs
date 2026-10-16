//! EXPORT002: cross-target parity. The same token must resolve to the same value in the CSS, the
//! JSON, the USS and the C# exports; a hand-edited or stale file makes one target disagree with
//! the rest (the drift the Unity and web outputs of one design system fall into).

// frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8

use crunk_tokens::export;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};

/// A token that resolves to different values in two export targets.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "EXPORT002",
    slug = "export-parity",
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
pub struct Export002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Export002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(spec) = host.spec() else {
            return;
        };
        match export::check_parity(spec) {
            Ok(found) => {
                for d in found {
                    tracing::debug!(token = %d.token, "EXPORT002: targets disagree");
                    out.fire_in(
                        "crunk.toml",
                        0,
                        format!(
                            "token `{}` is `{}` in {} but `{}` in {}; run `crunk tokens` to regenerate",
                            d.token,
                            d.left_value,
                            d.left.name(),
                            d.right_value,
                            d.right.name()
                        ),
                    );
                }
            }
            Err(err) => {
                tracing::warn!(%err, "EXPORT002: parity cannot be decided");
                out.unresolved(format!("the exports cannot be compared: {err}"));
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Export002 {
    fn subjects(&self, host: &P) -> usize {
        usize::from(host.spec().is_some())
    }
}
