//! CI001: An external `uses:` that is not pinned to a full commit SHA.

// frob:ticket 01M5F010QB00AR00D4HYVYYPWH

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::CiHost;

/// An external `uses:` that is not pinned to a full commit SHA.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CI001",
    slug = "pinned-ref",
    severity = Warn,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = CiHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Ci001;

impl<P: ?Sized + CiHost> RepoRule<P> for Ci001 {
    /// The verdict is computed by the product pipeline; see the crate doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + CiHost> Measured<P> for Ci001 {
    fn subjects(&self, host: &P) -> usize {
        host.ci_subjects_of("CI001")
    }
}
