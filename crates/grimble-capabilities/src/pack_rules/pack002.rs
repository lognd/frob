//! PACK002: A pack references a capability atom that is not in the atom registry.

// frob:ticket 01M3ZX7K3N8AWVBTZ90E0F1YSP

use gob_rules::{Out, RepoRule, rule};

use super::host::PackHost;

/// A pack references a capability atom that is not in the atom registry.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PACK002",
    slug = "pack-unknown-atom",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = PackHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Pack002;

impl<P: ?Sized + PackHost> RepoRule<P> for Pack002 {
    /// The verdict is computed by the pack pass (`evaluate`); see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
