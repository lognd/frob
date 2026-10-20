//! B1 acceptance tests: plan and handwritten findings are equal, and the gate fails above 1.3x.
#![allow(missing_docs, reason = "test harness crate")]

#[allow(
    dead_code,
    reason = "the timing helpers belong to the other bench target"
)]
mod b1;

use b1::{BenchError, LIMIT, cases, check_equal, fixture, gate, median, prepare};

/// Small fixture, every rule: the plan and the handwritten form return equal findings.
#[test]
fn b1_findings_equal() {
    let cases = cases().expect("rules compile");
    let (rust, md) = fixture::corpus(3, 200, 3, 100);
    let mut total = [0usize; 3];
    for (i, case) in cases.iter().enumerate() {
        let (files, lang) = if case.id == "DOC002" {
            (&md, "markdown")
        } else {
            (&rust, "rust")
        };
        for f in files {
            let p = prepare(f, lang).expect("fixture models");
            total[i] += check_equal(case, &p).unwrap_or_else(|e| panic!("{e}"));
        }
    }
    assert!(
        total.iter().all(|&n| n > 0),
        "every rule finds something: {total:?}"
    );
}

/// The gate passes at the limit and fails above it.
#[test]
fn b1_gate_fails_above_limit() {
    assert!(gate("TODO001", LIMIT, LIMIT).is_ok());
    assert!(matches!(
        gate("TODO001", 1.31, LIMIT),
        Err(BenchError::OverBudget { .. })
    ));
    assert!((median(&[3.0, 1.0, 2.0]) - 2.0).abs() < f64::EPSILON);
}
