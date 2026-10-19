//! Percentiles by linear interpolation between order statistics (the common "type 7" estimate).
// frob:ticket 01M48Q2AQXY69YKK3D2DC05ZWR

use schemars::JsonSchema;
use serde::Serialize;

/// The 50th, 85th and 95th percentile of a sample.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, JsonSchema)]
pub struct Percentiles {
    /// Median.
    pub p50: f64,
    /// 85th percentile: the usual "plan to this" service-level figure.
    pub p85: f64,
    /// 95th percentile.
    pub p95: f64,
}

/// The `p` quantile (0..=1) of `sorted` ascending, `None` when empty.
pub fn quantile(sorted: &[f64], p: f64) -> Option<f64> {
    let last = sorted.len().checked_sub(1)?;
    #[allow(clippy::cast_precision_loss)]
    let pos = p.clamp(0.0, 1.0) * last as f64;
    // Truncation intended: floor of a non-negative position inside the slice.
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    let lo = pos.floor() as usize;
    let hi = (lo + 1).min(last);
    #[allow(clippy::cast_precision_loss)]
    let frac = pos - lo as f64;
    Some(sorted[lo] + (sorted[hi] - sorted[lo]) * frac)
}

/// P50/P85/P95 of `samples` (any order), `None` when empty.
pub fn percentiles(samples: &[f64]) -> Option<Percentiles> {
    let mut sorted: Vec<f64> = samples.iter().copied().filter(|v| v.is_finite()).collect();
    sorted.sort_by(f64::total_cmp);
    Some(Percentiles {
        p50: quantile(&sorted, 0.50)?,
        p85: quantile(&sorted, 0.85)?,
        p95: quantile(&sorted, 0.95)?,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ten_samples_have_known_percentiles() {
        // frob:tests crates/frob-metrics/src/percentile.rs::percentiles
        let s: Vec<f64> = (1..=10).rev().map(f64::from).collect();
        let p = percentiles(&s).expect("non-empty");
        assert!((p.p50 - 5.5).abs() < 1e-9);
        assert!((p.p85 - 8.65).abs() < 1e-9);
        assert!((p.p95 - 9.55).abs() < 1e-9);
        assert!(percentiles(&[]).is_none());
    }
}
