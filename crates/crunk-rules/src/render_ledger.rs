//! The render ledger STATE004 and STATE005 read: which `(screen, state, platform)` cells already have a render.
//! The product gathers it from the gallery manifest; the rule only compares it with the spec's cells.

// frob:ticket 01M5EF4A7DQJQ2SHXYAYCAB73X
// frob:ticket 01M5EF4A9VM42NW2805KJJ86Q4

use std::collections::BTreeSet;

/// Smallest pixel difference between two states of one screen on one platform, in parts per million.
pub const MIN_STATE_DIFF_PPM: u32 = 10_000;

/// The measured pixel difference between two states of one screen rendered on one platform.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StateDiff {
    /// The screen both states belong to.
    pub screen: String,
    /// The platform both renders were made on.
    pub platform: String,
    /// The first state id.
    pub a: String,
    /// The second state id.
    pub b: String,
    /// Share of differing pixels in parts per million (`1_000_000` means every pixel differs).
    pub diff_ppm: u32,
}

/// The cells that have a render, plus why the ledger could not be read when it could not.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct RenderLedger {
    /// `(screen, state, platform)` ids with a render on record.
    pub rendered: BTreeSet<(String, String, String)>,
    /// Why the ledger could not be read (an unreadable or invalid manifest), when it could not.
    pub unreadable: Option<String>,
    // frob:ticket 01M5EF4A9VM42NW2805KJJ86Q4
    /// Pairwise state differences measured from the renders (STATE005's input).
    pub diffs: Vec<StateDiff>,
}

impl RenderLedger {
    /// Record that `state` of `screen` has a render on `platform`.
    pub fn record(&mut self, screen: &str, state: &str, platform: &str) {
        tracing::debug!(screen, state, platform, "render ledger entry recorded");
        self.rendered
            .insert((screen.to_owned(), state.to_owned(), platform.to_owned()));
    }

    // frob:ticket 01M5EF4A9VM42NW2805KJJ86Q4
    /// Record the measured difference between states `a` and `b` of `screen` on `platform`.
    pub fn record_diff(&mut self, screen: &str, platform: &str, a: &str, b: &str, diff_ppm: u32) {
        tracing::debug!(screen, platform, a, b, diff_ppm, "state diff recorded");
        self.diffs.push(StateDiff {
            screen: screen.to_owned(),
            platform: platform.to_owned(),
            a: a.to_owned(),
            b: b.to_owned(),
            diff_ppm,
        });
    }

    /// True when `state` of `screen` has a render on `platform`.
    pub fn has(&self, screen: &str, state: &str, platform: &str) -> bool {
        self.rendered
            .contains(&(screen.to_owned(), state.to_owned(), platform.to_owned()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn has_sees_only_recorded_cells() {
        let mut ledger = RenderLedger::default();
        ledger.record("home", "default", "desk");
        assert!(ledger.has("home", "default", "desk"));
        assert!(!ledger.has("home", "default", "phone"));
    }
}
