//! B2 acceptance tests: disk and compiled-in findings serialize to identical JSON, and the gate
//! fails above 1.3x.
#![allow(missing_docs, reason = "test harness crate")]
#![allow(
    dead_code,
    reason = "the timing helpers belong to the other bench target"
)]

mod b2;

use b2::{
    BenchError, LIMIT, cases, compiled_plan, disk_plan, findings_json, fixture, gate, pair, prepare,
};

/// Small fixture, every rule: the two runs produce identical JSON.
#[test]
fn b2_json_identical() {
    let cases = cases().expect("rules compile");
    let (rust, md) = fixture::corpus(3, 200, 3, 100);
    for case in &cases {
        let (files, lang) = if case.id == "DOC002" {
            (&md, "markdown")
        } else {
            (&rust, "rust")
        };
        let prepared: Vec<_> = files
            .iter()
            .map(|f| prepare(f, lang).expect("models"))
            .collect();
        let p = pair(case).expect("pair");
        let compiled = findings_json(case, &compiled_plan(&p).unwrap(), &prepared).unwrap();
        let disk = findings_json(case, &disk_plan(&p).unwrap(), &prepared).unwrap();
        let found = compiled["files"]
            .as_array()
            .unwrap()
            .iter()
            .map(|f| f["findings"].as_array().unwrap().len())
            .sum::<usize>();
        assert!(found > 0, "{} finds something", case.id);
        assert_eq!(compiled.to_string(), disk.to_string(), "{}", case.id);
    }
}

/// The gate passes at the limit and fails above it.
#[test]
fn b2_gate_fails_above_limit() {
    assert!(gate("TODO001", LIMIT, LIMIT).is_ok());
    assert!(matches!(
        gate("TODO001", 1.31, LIMIT),
        Err(BenchError::OverBudget { .. })
    ));
}
