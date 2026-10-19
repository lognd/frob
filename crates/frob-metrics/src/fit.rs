//! Log-normal cost fit: `ln(cost) = a + b * ln(points) + e`, `e ~ N(0, sigma^2)`, by ordinary least squares on the log scale.
//!
//! The fit gives a median and P85 per size, the geometric spread `exp(sigma)` and the exponent `b`
//! (1 = cost proportional to points) with a 95% interval from the Student-t distribution.
// frob:ticket 01M48Q2AQXY69YKK3D2DC05ZWR

use schemars::JsonSchema;
use serde::Serialize;

/// z-score of the 85th percentile of the standard normal.
pub const Z85: f64 = 1.036_433_389_493_789_8;
/// z-score of the two-sided 95% normal interval.
const Z975: f64 = 1.959_963_984_540_054;
/// Fewest samples a fit can use: two parameters plus one residual degree of freedom.
pub const MIN_SAMPLES: usize = 3;

/// Why a fit could not be made.
#[derive(Debug, Clone, PartialEq, thiserror::Error)]
pub enum FitError {
    /// Fewer than [`MIN_SAMPLES`] usable samples.
    #[error("E-METRICS-SAMPLES: {have} usable samples, a fit needs {MIN_SAMPLES}")]
    TooFew {
        /// Usable samples given.
        have: usize,
    },
    /// A point count or cost was not strictly positive and finite.
    #[error(
        "E-METRICS-DOMAIN: sample {index} has points {points} and cost {cost}; both must be positive"
    )]
    NonPositive {
        /// Index of the offending sample.
        index: usize,
        /// Its points.
        points: f64,
        /// Its cost.
        cost: f64,
    },
}

/// A fitted log-normal cost model.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, JsonSchema)]
pub struct LogNormalFit {
    /// Samples used.
    pub samples: u32,
    /// Intercept `a`: `exp(a)` is the median cost of a one-point ticket.
    pub a: f64,
    /// Exponent `b` on the log of points.
    pub b: f64,
    /// 95% interval of `b`; absent when every sample had the same points (no slope to estimate).
    pub b_interval: Option<(f64, f64)>,
    /// Residual standard deviation on the log scale.
    pub sigma: f64,
    /// Geometric spread `exp(sigma)`: a typical multiplicative miss around the median.
    pub spread: f64,
}

/// The modelled cost of a ticket of one size.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, JsonSchema)]
pub struct SizePrediction {
    /// Story points.
    pub points: u32,
    /// Median cost.
    pub median: f64,
    /// 85th percentile cost.
    pub p85: f64,
    /// Median cost divided by points.
    pub median_per_point: f64,
}

/// The 97.5% Student-t quantile for `dof` degrees of freedom (Cornish-Fisher expansion about the normal).
fn t975(dof: f64) -> f64 {
    let z = Z975;
    let (z3, z5) = (z.powi(3), z.powi(5));
    z + (z3 + z) / (4.0 * dof) + (5.0 * z5 + 16.0 * z3 + 3.0 * z) / (96.0 * dof * dof)
}

/// Fit `(points, cost)` samples on the log scale.
///
/// # Errors
///
/// [`FitError::NonPositive`] for a non-positive or non-finite sample, [`FitError::TooFew`] under [`MIN_SAMPLES`].
pub fn fit(samples: &[(f64, f64)]) -> Result<LogNormalFit, FitError> {
    if samples.len() < MIN_SAMPLES {
        return Err(FitError::TooFew {
            have: samples.len(),
        });
    }
    let mut logs = Vec::with_capacity(samples.len());
    for (index, &(points, cost)) in samples.iter().enumerate() {
        if !(points.is_finite() && cost.is_finite() && points > 0.0 && cost > 0.0) {
            return Err(FitError::NonPositive {
                index,
                points,
                cost,
            });
        }
        logs.push((points.ln(), cost.ln()));
    }
    #[allow(clippy::cast_precision_loss)]
    let n = logs.len() as f64;
    let xbar = logs.iter().map(|l| l.0).sum::<f64>() / n;
    let ybar = logs.iter().map(|l| l.1).sum::<f64>() / n;
    let sxx = logs.iter().map(|l| (l.0 - xbar).powi(2)).sum::<f64>();
    let sxy = logs
        .iter()
        .map(|l| (l.0 - xbar) * (l.1 - ybar))
        .sum::<f64>();
    let slope = sxx > 1e-12;
    let b = if slope { sxy / sxx } else { 0.0 };
    let a = ybar - b * xbar;
    let rss = logs
        .iter()
        .map(|l| (l.1 - (a + b * l.0)).powi(2))
        .sum::<f64>();
    let dof = if slope { n - 2.0 } else { n - 1.0 };
    let sigma = (rss / dof).sqrt();
    let b_interval = slope.then(|| {
        let half = t975(dof) * sigma / sxx.sqrt();
        (b - half, b + half)
    });
    tracing::debug!(n, a, b, sigma, "log-normal cost fit");
    Ok(LogNormalFit {
        samples: u32::try_from(logs.len()).unwrap_or(u32::MAX),
        a,
        b,
        b_interval,
        sigma,
        spread: sigma.exp(),
    })
}

impl LogNormalFit {
    /// Median cost of a `points`-point ticket.
    pub fn median(&self, points: f64) -> f64 {
        (self.a + self.b * points.ln()).exp()
    }

    /// 85th percentile cost of a `points`-point ticket.
    pub fn p85(&self, points: f64) -> f64 {
        (self.a + self.b * points.ln() + Z85 * self.sigma).exp()
    }

    /// Median and P85 for each of `sizes` (story points, all positive).
    pub fn predict(&self, sizes: &[u32]) -> Vec<SizePrediction> {
        sizes
            .iter()
            .filter(|&&p| p > 0)
            .map(|&p| {
                let pf = f64::from(p);
                let median = self.median(pf);
                SizePrediction {
                    points: p,
                    median,
                    p85: self.p85(pf),
                    median_per_point: median / pf,
                }
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Deterministic standard normals: an LCG feeding Box-Muller, so the test needs no RNG crate.
    fn normals(n: usize) -> Vec<f64> {
        let mut state: u64 = 0x2545_F491_4F6C_DD1D;
        let mut next = move || {
            state = state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            #[allow(clippy::cast_precision_loss)]
            let u = ((state >> 11) as f64 + 1.0) / ((1u64 << 53) as f64 + 1.0);
            u
        };
        (0..n)
            .map(|_| {
                let (u1, u2) = (next(), next());
                (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()
            })
            .collect()
    }

    #[test]
    fn fit_recovers_synthetic_log_normal_parameters() {
        // frob:tests crates/frob-metrics/src/fit.rs::fit
        let (a, b, sigma) = (1.2_f64, 0.8_f64, 0.3_f64);
        let sizes = [1.0, 2.0, 3.0, 5.0, 8.0];
        let samples: Vec<(f64, f64)> = normals(4000)
            .into_iter()
            .enumerate()
            .map(|(i, e)| {
                let p: f64 = sizes[i % sizes.len()];
                (p, (a + b * p.ln() + sigma * e).exp())
            })
            .collect();
        let f = fit(&samples).expect("fits");
        assert!((f.a - a).abs() < 0.03, "a = {}", f.a);
        assert!((f.b - b).abs() < 0.03, "b = {}", f.b);
        assert!((f.sigma - sigma).abs() < 0.02, "sigma = {}", f.sigma);
        let (lo, hi) = f.b_interval.expect("slope present");
        assert!(lo < b && b < hi, "interval ({lo}, {hi}) misses {b}");
        assert!((f.spread - sigma.exp()).abs() < 0.03);
        assert!(f.p85(3.0) > f.median(3.0));
    }

    #[test]
    fn a_fit_needs_three_positive_samples() {
        // frob:tests crates/frob-metrics/src/fit.rs::fit
        assert_eq!(
            fit(&[(1.0, 2.0), (2.0, 3.0)]),
            Err(FitError::TooFew { have: 2 })
        );
        assert!(matches!(
            fit(&[(1.0, 2.0), (2.0, 0.0), (3.0, 1.0)]),
            Err(FitError::NonPositive { index: 1, .. })
        ));
    }

    #[test]
    fn equal_points_fit_an_intercept_only() {
        // frob:tests crates/frob-metrics/src/fit.rs::fit
        let f = fit(&[(2.0, 4.0), (2.0, 4.0), (2.0, 4.0)]).expect("fits");
        assert!(f.b_interval.is_none());
        assert!((f.median(2.0) - 4.0).abs() < 1e-9);
    }
}
