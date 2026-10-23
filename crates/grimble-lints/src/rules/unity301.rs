//! UNITY301: The legacy Input class used in a project whose active input handler is the Input System.

// frob:ticket 01M5HGRWG7RDR3DTS7PT08HTWJ

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::UnityHost;

/// The legacy `Input` class used in a project whose active input handler is the Input System.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "UNITY301",
    slug = "legacy-input-under-input-system",
    severity = Warn,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = UnityHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Unity301;

impl<P: ?Sized + UnityHost> RepoRule<P> for Unity301 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + UnityHost> Measured<P> for Unity301 {
    fn subjects(&self, host: &P) -> usize {
        host.unity_subjects_of("UNITY301")
    }
}
