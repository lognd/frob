//! PACK004: A pack declares the same item more than once.

// frob:ticket 01M3ZX7K3N8AWVBTZ90E0F1YSP

use gob_rules::{Out, RepoRule, rule};

use super::host::PackHost;

/// A pack declares the same item more than once.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PACK004",
    slug = "pack-duplicate",
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
pub struct Pack004;

impl<P: ?Sized + PackHost> RepoRule<P> for Pack004 {
    /// The verdict is computed by the pack pass (`evaluate`); see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
