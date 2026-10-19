//! PACK001: An enabled pack differs from its lock entry (changed, added, removed item or lock-missing).

// frob:ticket 01M3ZX7K3N8AWVBTZ90E0F1YSP

use gob_rules::{Out, RepoRule, rule};

use super::host::PackHost;

/// An enabled pack differs from its lock entry (changed, added, removed item or lock-missing).
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PACK001",
    slug = "pack-lock-mismatch",
    severity = Error,
    polarity = P0,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = PackHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Pack001;

impl<P: ?Sized + PackHost> RepoRule<P> for Pack001 {
    /// The verdict is computed by the pack pass (`evaluate`); see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
