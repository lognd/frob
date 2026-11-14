//! Duration tokens read against the configured `[tokens] max_duration_ms` bound.

// frob:ticket 01M5XCVZBYWA5WCATMF9QYZAS8

use crunk_tokens::{Token, TokenSet, TokenValue};

/// Every token holding a duration (in its default or any mode value) longer than `max_ms`, with
/// that longest offending duration in milliseconds.
pub fn over_max(set: &TokenSet, max_ms: f64) -> Vec<(&Token, f64)> {
    set.iter()
        .filter_map(|t| {
            let longest = std::iter::once(&t.value)
                .chain(t.modes.values())
                .filter_map(|v| match v {
                    TokenValue::Duration(ms) => Some(*ms),
                    _ => None,
                })
                .fold(f64::NEG_INFINITY, f64::max);
            (longest > max_ms).then_some((t, longest))
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::over_max;

    // frob:tests crates/crunk-rules/src/token_timing.rs::over_max
    #[test]
    fn flags_only_durations_past_the_bound() {
        let set = crunk_tokens::dialect::parse(
            "[motion.fast]\nvalue = \"200ms\"\n[motion.slow]\nvalue = \"4s\"\n[color.ink]\nvalue = \"#101820\"\n",
            "t.toml",
        )
        .unwrap();
        let hits = over_max(&set, 1000.0);
        assert_eq!(hits.len(), 1);
        assert!((hits[0].1 - 4000.0).abs() < f64::EPSILON);
        assert!(over_max(&set, 4000.0).is_empty());
    }
}
