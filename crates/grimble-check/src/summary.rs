//! `grimble check --summary`: a compact digest of the `gob.sibling/1` document.
//!
//! A large model makes `check --json` megabytes of findings, entities and bindings, which is
//! too big to commit as file evidence. [`summary_document`] folds that document into counts per
//! rule and severity, the capability cells per node and two digests, so the summary stays under
//! [`SUMMARY_BUDGET`] bytes whatever the model size. The bound comes from aggregation, never
//! from truncation: when the per-node rows would not fit they are folded into per-signature
//! counts, then into totals, and `nodes_detail` names the tier that was kept.
//!
//! Capability cells are read from the CAP findings of the document: a CAP001 error is an
//! `undeclared` cell, a CAP001 unresolved site an `unknown` cell and a CAP002 finding a
//! `declared-unused` cell. A finding belongs to the node whose entity row has the same file and
//! byte range. The matrix cells that raise no finding (`uses`, `denied`, `excused`) are not in
//! the document and so are not in the summary.

// frob:ticket 01M4HEMDB8A1X1RQFNVJB1G32M

use std::collections::BTreeMap;

use serde_json::{Value, json};

use crate::config::blake3_tagged;

/// Schema tag of the summary document.
pub const SUMMARY_SCHEMA: &str = "grimble.check-summary/1";

/// Hard upper bound on the serialized summary: the size cap of file evidence.
pub const SUMMARY_BUDGET: usize = 64 * 1024;

/// Bytes the per-node section may take before it is folded into a coarser tier.
const NODE_BUDGET: usize = 16 * 1024;

/// The finding severities as the document spells them, in report order.
const SEVERITIES: [&str; 4] = ["error", "warning", "advisory", "unresolved"];

/// Capability cells that surface as findings, in report order.
const CELLS: [&str; 3] = ["undeclared", "declared-unused", "unknown"];

/// The `(file, start, end)` identity a finding and the entity it is about share.
type Site = (String, u64, u64);

/// A node's cell counts in [`CELLS`] order.
type Signature = [u64; 3];

fn site_of(row: &Value) -> Option<Site> {
    let range = row.get("range")?;
    Some((
        row.get("file")?.as_str()?.to_owned(),
        range.get("start")?.as_u64()?,
        range.get("end")?.as_u64()?,
    ))
}

fn cell_of(rule: &str, severity: &str) -> Option<usize> {
    match (rule, severity) {
        ("CAP001", "error") => Some(0),
        ("CAP002", _) => Some(1),
        ("CAP001", "unresolved") => Some(2),
        _ => None,
    }
}

fn str_of<'a>(row: &'a Value, key: &str) -> &'a str {
    row.get(key).and_then(Value::as_str).unwrap_or_default()
}

/// Rows `{rule, error, warning, advisory, unresolved, suppressed}` for each rule with a finding.
fn by_rule(doc: &Value) -> Vec<Value> {
    let mut rows: BTreeMap<String, ([u64; 4], u64)> = BTreeMap::new();
    for f in doc["findings"].as_array().into_iter().flatten() {
        let entry = rows.entry(str_of(f, "rule").to_owned()).or_default();
        if let Some(i) = SEVERITIES.iter().position(|s| *s == str_of(f, "severity")) {
            entry.0[i] += 1;
        }
    }
    for s in doc["suppressed"].as_array().into_iter().flatten() {
        let rule = s.get("finding").map_or("", |f| str_of(f, "rule"));
        rows.entry(rule.to_owned()).or_default().1 += 1;
    }
    rows.into_iter()
        .map(|(rule, (c, suppressed))| {
            json!({
                "rule": rule, "error": c[0], "warning": c[1], "advisory": c[2],
                "unresolved": c[3], "suppressed": suppressed,
            })
        })
        .collect()
}

/// Cell counts per node anchor, plus how many CAP findings matched no node.
fn node_cells(doc: &Value) -> (BTreeMap<String, Signature>, u64) {
    let mut nodes: BTreeMap<String, Signature> = BTreeMap::new();
    let mut by_site: BTreeMap<Site, String> = BTreeMap::new();
    for e in doc["entities"].as_array().into_iter().flatten() {
        if str_of(e, "kind") == "node"
            && let Some(site) = site_of(e)
        {
            let anchor = str_of(e, "anchor").to_owned();
            nodes.entry(anchor.clone()).or_default();
            by_site.insert(site, anchor);
        }
    }
    let mut unattributed = 0;
    for f in doc["findings"].as_array().into_iter().flatten() {
        let Some(cell) = cell_of(str_of(f, "rule"), str_of(f, "severity")) else {
            continue;
        };
        match site_of(f).and_then(|s| by_site.get(&s)) {
            Some(anchor) => nodes.entry(anchor.clone()).or_default()[cell] += 1,
            None => unattributed += 1,
        }
    }
    (nodes, unattributed)
}

fn signature_json(sig: Signature) -> Value {
    let mut cells = serde_json::Map::new();
    for (name, n) in CELLS.iter().zip(sig) {
        cells.insert((*name).to_owned(), json!(n));
    }
    Value::Object(cells)
}

/// The per-node section at the finest tier whose rows fit [`NODE_BUDGET`].
///
/// Returns the tier name and its value. Nodes with no cell finding are only counted.
fn node_section(nodes: &BTreeMap<String, Signature>) -> (&'static str, Value) {
    let flagged: Vec<(&String, &Signature)> = nodes.iter().filter(|(_, s)| **s != [0; 3]).collect();
    let rows: Vec<Value> = flagged
        .iter()
        .map(|(anchor, s)| {
            let mut row = signature_json(**s);
            row["node"] = json!(anchor);
            row
        })
        .collect();
    let rows = Value::Array(rows);
    if rows.to_string().len() <= NODE_BUDGET {
        return ("per-node", rows);
    }
    let mut groups: BTreeMap<Signature, u64> = BTreeMap::new();
    for (_, s) in &flagged {
        *groups.entry(**s).or_default() += 1;
    }
    let groups = Value::Array(
        groups
            .into_iter()
            .map(|(s, n)| {
                let mut row = signature_json(s);
                row["nodes"] = json!(n);
                row
            })
            .collect(),
    );
    if groups.to_string().len() <= NODE_BUDGET {
        return ("per-signature", groups);
    }
    ("totals", Value::Array(Vec::new()))
}

/// Digest of the whole document minus `timing`, the only field that varies between runs.
fn document_digest(doc: &Value) -> String {
    let mut stable = doc.clone();
    if let Some(map) = stable.as_object_mut() {
        map.remove("timing");
    }
    blake3_tagged(stable.to_string().as_bytes())
}

/// Fold the `gob.sibling/1` document `doc` into the compact summary.
///
/// The result is under [`SUMMARY_BUDGET`] bytes for any input, lists findings per rule and
/// severity and capability cells per node, and carries `compute_digest` (copied) and
/// `document_digest` (of the full document) so the full document can be matched to it.
#[must_use]
pub fn summary_document(doc: &Value) -> Value {
    let mut totals = [0_u64; 4];
    for f in doc["findings"].as_array().into_iter().flatten() {
        if let Some(i) = SEVERITIES.iter().position(|s| *s == str_of(f, "severity")) {
            totals[i] += 1;
        }
    }
    let (nodes, unattributed) = node_cells(doc);
    let mut cell_totals = [0_u64; 3];
    for s in nodes.values() {
        for (t, n) in cell_totals.iter_mut().zip(s) {
            *t += n;
        }
    }
    let (detail, rows) = node_section(&nodes);
    let summary = json!({
        "schema_version": SUMMARY_SCHEMA,
        "product": doc["product"],
        "product_version": doc["product_version"],
        "compute_digest": doc["compute_digest"],
        "document_digest": document_digest(doc),
        "document_schema": doc["schema_version"],
        "findings": {
            "total": totals.iter().sum::<u64>(),
            "by_severity": {
                "error": totals[0], "warning": totals[1],
                "advisory": totals[2], "unresolved": totals[3],
            },
            "suppressed": doc["suppressed"].as_array().map_or(0, Vec::len),
            "by_rule": by_rule(doc),
        },
        "capabilities": {
            "nodes": nodes.len(),
            "cells": signature_json(cell_totals),
            "unattributed_findings": unattributed,
            "nodes_detail": detail,
            "by_node": rows,
        },
    });
    tracing::debug!(
        bytes = summary.to_string().len(),
        nodes = nodes.len(),
        detail,
        "check summary built"
    );
    summary
}
