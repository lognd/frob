//! PACK003: A pack's detector is unavailable, so its detections are skipped.

// frob:ticket 01M3ZX7K3N8AWVBTZ90E0F1YSP

use gob_rules::{Out, RepoRule, rule};

use super::host::PackHost;

/// A pack's detector is unavailable, so its detections are skipped.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "PACK003",
    slug = "pack-detector-unavailable",
    severity = Warn,
    polarity = P0,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = project,
    host = PackHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Pack003;

impl<P: ?Sized + PackHost> RepoRule<P> for Pack003 {
    /// The verdict is computed by the pack pass (`evaluate`); see the module doc.
    fn check(&self, _host: &P, _out: &mut Out<'_, Self>) {}
}
