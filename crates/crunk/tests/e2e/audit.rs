//! The mapping audit: every captured Python test maps to a Rust test or a reasoned drop.

use std::collections::BTreeSet;

use serde::Deserialize;
use serde_json::Value;

use crate::replay::{entry_name, parity_root};

#[derive(Deserialize)]
struct Mapping {
    row: Vec<Row>,
}

/// One mapping row: a Python node and what replaces it.
#[derive(Deserialize)]
struct Row {
    node: String,
    ids: Vec<String>,
    rust: Option<String>,
    dropped: Option<String>,
}

/// Whether `source` holds `#[test] fn <name>(`.
fn has_test(source: &str, name: &str) -> bool {
    let needle = format!("fn {name}(");
    let lines: Vec<&str> = source.lines().collect();
    lines.iter().enumerate().any(|(i, l)| {
        l.trim_start().starts_with(&needle)
            && i > 0
            && lines[..i]
                .iter()
                .rev()
                .map(|p| p.trim())
                .find(|p| !p.starts_with("//"))
                == Some("#[test]")
    })
}

/// The Python nodes and index ids the audit must see mapped.
pub fn required() -> (BTreeSet<String>, BTreeSet<String>) {
    let root = parity_root();
    let text = std::fs::read_to_string(root.join("index.json")).expect("index.json");
    let index: Value = serde_json::from_str(&text).expect("index json");
    let (mut nodes, mut ids) = (BTreeSet::new(), BTreeSet::new());
    for (id, entry) in index["e2e_int"].as_object().expect("e2e_int") {
        ids.insert(id.clone());
        if id.starts_with("INT") {
            nodes.insert(entry["source"].as_str().expect("source").to_owned());
        }
        for scenario in entry["scenarios"].as_array().into_iter().flatten() {
            let dir = root
                .join("fixtures/e2e")
                .join(scenario.as_str().expect("scenario"));
            for file in std::fs::read_dir(&dir).expect("scenario dir").flatten() {
                if entry_name(&file).ends_with(".step.json") {
                    let step: Value =
                        serde_json::from_str(&std::fs::read_to_string(file.path()).expect("step"))
                            .expect("step json");
                    nodes.insert(step["node"].as_str().expect("node").to_owned());
                }
            }
        }
    }
    (nodes, ids)
}

/// Every audit problem for `mapping` against the Rust `sources` and the required nodes and ids.
pub fn audit(
    mapping: &str,
    sources: &[&str],
    nodes: &BTreeSet<String>,
    ids: &BTreeSet<String>,
) -> Vec<String> {
    let parsed: Mapping = toml::from_str(mapping).expect("mapping.toml");
    let mut problems = Vec::new();
    let mapped: BTreeSet<&str> = parsed.row.iter().map(|r| r.node.as_str()).collect();
    let mapped_ids: BTreeSet<&str> = parsed
        .row
        .iter()
        .flat_map(|r| r.ids.iter().map(String::as_str))
        .collect();
    for node in nodes.iter().filter(|n| !mapped.contains(n.as_str())) {
        problems.push(format!("python test {node} has no mapping row"));
    }
    for id in ids.iter().filter(|i| !mapped_ids.contains(i.as_str())) {
        problems.push(format!("{id} appears in no mapping row"));
    }
    for row in &parsed.row {
        match (&row.rust, &row.dropped) {
            (Some(name), None) => {
                if !sources.iter().any(|s| has_test(s, name)) {
                    problems.push(format!("{} maps to missing rust test {name}", row.node));
                }
            }
            (None, Some(reason)) if !reason.trim().is_empty() => {}
            _ => problems.push(format!(
                "{} needs exactly one of rust or a non-empty dropped reason",
                row.node
            )),
        }
    }
    problems
}
