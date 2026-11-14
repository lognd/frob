//! `[tokens] max_duration_ms`: the longest duration token the TOKEN010 bound check allows.

// frob:ticket 01M5XCVZBYWA5WCATMF9QYZAS8

use crate::validate::{Res, fail, keys};

/// Validate the configured duration bound: unset, or a finite number greater than zero.
pub(crate) fn max_duration(raw: Option<f64>) -> Res<Option<f64>> {
    match raw {
        Some(ms) if !ms.is_finite() || ms <= 0.0 => {
            tracing::warn!(ms, "max_duration_ms rejected");
            Err(fail(
                keys(&["tokens", "max_duration_ms"]),
                "must be greater than zero",
            ))
        }
        other => Ok(other),
    }
}

#[cfg(test)]
mod tests {
    use super::max_duration;

    // frob:tests crates/crunk-spec/src/timing.rs::max_duration
    #[test]
    fn max_duration_bounds() {
        assert_eq!(max_duration(None).unwrap(), None);
        assert_eq!(max_duration(Some(1000.0)).unwrap(), Some(1000.0));
        assert!(max_duration(Some(0.0)).is_err());
        assert!(max_duration(Some(-5.0)).is_err());
        assert!(max_duration(Some(f64::NAN)).is_err());
    }
}
