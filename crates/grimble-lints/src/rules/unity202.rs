//! UNITY202: A managed allocation (collection, StringBuilder, array) in code Unity runs every frame.

// frob:ticket 01M5HPSP14N3NCX5TNA9XDR1GY

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::UnityHost;

/// A managed allocation (collection, `StringBuilder`, array) in code Unity runs every frame.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "UNITY202",
    slug = "allocation-in-hot-code",
    severity = Error,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = UnityHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Unity202;

impl<P: ?Sized + UnityHost> RepoRule<P> for Unity202 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + UnityHost> Measured<P> for Unity202 {
    fn subjects(&self, host: &P) -> usize {
        host.unity_subjects_of("UNITY202")
    }
}
