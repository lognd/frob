//! EXPORT001: a generated token export (CSS, Tailwind, JSON, USS, C#, DTCG) that is missing or
//! differs from what the spec renders now, named by target. This generalises TOKENS001, which
//! reports the same files without saying which export they belong to.

// frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8

use crunk_tokens::export;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::site_path;
use crate::tokens_drift::drift_message;

/// A generated export file, named by target, that is missing or has drifted from the spec.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "EXPORT001",
    slug = "export-drift",
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
pub struct Export001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Export001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let Some(spec) = host.spec() else {
            return;
        };
        match export::check(spec) {
            Ok(report) => {
                for file in report.dirty() {
                    let path = site_path(spec, &file.path);
                    tracing::debug!(%path, target = file.target.name(), "EXPORT001: drifted export");
                    out.fire_in(
                        &path,
                        0,
                        format!(
                            "{} export: {}",
                            file.target.name(),
                            drift_message(file.status, file.banner_only)
                        ),
                    );
                }
            }
            Err(err) => {
                tracing::warn!(%err, "EXPORT001: drift cannot be decided");
                out.unresolved(format!("the exports cannot be compared: {err}"));
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Export001 {
    fn subjects(&self, host: &P) -> usize {
        usize::from(host.spec().is_some())
    }
}
