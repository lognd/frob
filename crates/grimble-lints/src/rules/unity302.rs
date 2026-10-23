//! UNITY302: A Rigidbody force or move applied from Update or LateUpdate instead of FixedUpdate.

// frob:ticket 01M5HGRWG7RDR3DTS7PT08HTWJ

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::UnityHost;

/// A Rigidbody force or move applied from `Update` or `LateUpdate` instead of `FixedUpdate`.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "UNITY302",
    slug = "physics-force-outside-fixed-update",
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
pub struct Unity302;

impl<P: ?Sized + UnityHost> RepoRule<P> for Unity302 {
    /// The verdict is computed by the product pipeline; see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}

impl<P: ?Sized + UnityHost> Measured<P> for Unity302 {
    fn subjects(&self, host: &P) -> usize {
        host.unity_subjects_of("UNITY302")
    }
}
