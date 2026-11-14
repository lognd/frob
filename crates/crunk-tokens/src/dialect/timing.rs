//! Bounds on authored easing curves: a cubic-bezier's x ordinates lie in `0..=1`.
//!
//! CSS rejects `cubic-bezier()` with an x outside that range, so the dialect rejects it at the
//! token, with the file and token path, instead of exporting a value no platform accepts.

// frob:ticket 01M5XCVZBYWA5WCATMF9QYZAS8

/// Why a cubic-bezier is out of bounds, or `None` when its x ordinates are in `0..=1`.
pub(super) fn bezier_problem(points: [f64; 4]) -> Option<String> {
    let [x1, _, x2, _] = points;
    let bad = [("x1", x1), ("x2", x2)]
        .into_iter()
        .find(|(_, x)| !(0.0..=1.0).contains(x))?;
    tracing::debug!(axis = bad.0, value = bad.1, "cubic bezier x out of range");
    Some(format!(
        "cubic bezier {} = {} is outside 0..1 (the x ordinates must lie in 0..1)",
        bad.0, bad.1
    ))
}

#[cfg(test)]
mod tests {
    use super::bezier_problem;

    // frob:tests crates/crunk-tokens/src/dialect/timing.rs::bezier_problem
    #[test]
    fn bezier_x_bounds() {
        assert!(bezier_problem([0.4, 0.0, 0.2, 1.0]).is_none());
        assert!(bezier_problem([0.4, -2.0, 0.2, 3.0]).is_none());
        assert!(bezier_problem([1.4, 0.0, 0.2, 1.0]).unwrap().contains("x1"));
        assert!(
            bezier_problem([0.4, 0.0, -0.1, 1.0])
                .unwrap()
                .contains("x2")
        );
    }
}
