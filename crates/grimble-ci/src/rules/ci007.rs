//! CI007: An attacker-influenced expression spliced into a `run:` script.

// frob:ticket 01M5F010QB00AR00D4HYVYYPWH

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CiHost;

/// An attacker-influenced expression spliced into a `run:` script.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI007",
    slug = "no-event-interpolation-in-run",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CiHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Ci007;

impl<P: ?Sized + CiHost> RepoRule<P> for Ci007 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CiHost> Measured<P> for Ci007 {
    fn subjects(&self, host: &P) -> usize {
        host.ci_subjects_of("CI007")
    }
}
