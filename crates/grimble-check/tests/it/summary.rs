//! `summary_document`: the size bound holds by aggregation and the output is deterministic.

// frob:ticket 01M4HEMDB8A1X1RQFNVJB1G32M

use grimble_check::{SUMMARY_BUDGET, summary_document};
use serde_json::{Value, json};

fn finding(rule: &str, severity: &str, node: usize) -> Value {
    json!({"rule": rule, "severity": severity, "file": "m.grmb",
           "range": {"start": node, "end": node + 1}})
}

/// Node `i` gets `i % 8` undeclared, `(i / 8) % 8` unused and `(i / 64) % 8` unknown cells.
fn document(nodes: usize) -> Value {
    let mut entities = Vec::new();
    let mut findings = Vec::new();
    for i in 0..nodes {
        entities.push(
            json!({"kind": "node", "anchor": format!("m.n{i}"), "file": "m.grmb",
                             "range": {"start": i, "end": i + 1}}),
        );
        for _ in 0..i % 8 {
            findings.push(finding("CAP001", "error", i));
        }
        for _ in 0..(i / 8) % 8 {
            findings.push(finding("CAP002", "warning", i));
        }
        for _ in 0..(i / 64) % 8 {
            findings.push(finding("CAP001", "unresolved", i));
        }
    }
    json!({"product": "grimble", "product_version": "0", "schema_version": "gob.sibling/1",
           "compute_digest": "blake3:abc", "timing": {"elapsed_ms": 1},
           "entities": entities, "findings": findings, "suppressed": []})
}

// frob:tests crates/grimble-check/src/summary.rs::summary_document
#[test]
fn many_distinct_nodes_fold_to_totals_within_budget() {
    let doc = document(512);
    let summary = summary_document(&doc);
    assert!(summary.to_string().len() < SUMMARY_BUDGET);
    assert_eq!(summary["capabilities"]["nodes_detail"], "totals");
    assert_eq!(summary["capabilities"]["nodes"], 512);
    // Aggregation keeps the totals exact: 64 nodes per undeclared level 0..8 sum to 64 * 28.
    assert_eq!(summary["capabilities"]["cells"]["undeclared"], 64 * 28);
    assert_eq!(summary["compute_digest"], "blake3:abc");
}

#[test]
fn few_nodes_keep_the_per_node_tier() {
    let doc = document(64);
    let summary = summary_document(&doc);
    assert_eq!(summary["capabilities"]["nodes_detail"], "per-node");
}

#[test]
fn digest_ignores_timing_but_not_content() {
    let a = document(10);
    let mut b = a.clone();
    b["timing"] = json!({"elapsed_ms": 99});
    assert_eq!(
        summary_document(&a)["document_digest"],
        summary_document(&b)["document_digest"]
    );
    b["findings"].as_array_mut().unwrap().pop();
    assert_ne!(
        summary_document(&a)["document_digest"],
        summary_document(&b)["document_digest"]
    );
}

#[test]
fn unmatched_cap_findings_are_counted_not_dropped() {
    let mut doc = document(1);
    doc["findings"] = json!([finding("CAP001", "error", 99)]);
    let summary = summary_document(&doc);
    assert_eq!(summary["capabilities"]["unattributed_findings"], 1);
    assert_eq!(summary["findings"]["total"], 1);
}
