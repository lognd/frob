//! The render ledger STATE004 reads: which `(screen, state, platform)` cells already have a render.
//! The product gathers it from the gallery manifest; the rule only compares it with the spec's cells.

// frob:ticket 01M5EF4A7DQJQ2SHXYAYCAB73X

use std::collections::BTreeSet;

/// The cells that have a render, plus why the ledger could not be read when it could not.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct RenderLedger {
    /// `(screen, state, platform)` ids with a render on record.
    pub rendered: BTreeSet<(String, String, String)>,
    /// Why the ledger could not be read (an unreadable or invalid manifest), when it could not.
    pub unreadable: Option<String>,
}

impl RenderLedger {
    /// Record that `state` of `screen` has a render on `platform`.
    pub fn record(&mut self, screen: &str, state: &str, platform: &str) {
        tracing::debug!(screen, state, platform, "render ledger entry recorded");
        self.rendered
            .insert((screen.to_owned(), state.to_owned(), platform.to_owned()));
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
