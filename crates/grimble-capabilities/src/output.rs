//! Matrix output and the census (grimble-model.md 9.6): the cells as text and cell counts.

// frob:ticket 01M59RWT16TFNSACMMTTXX200T

use std::collections::BTreeMap;
use std::fmt::Write as _;

use crate::{Cell, Matrix};

/// The matrix as text: one `node atom cell` line per non-`denied` cell, sorted.
pub fn render(m: &Matrix) -> String {
    let mut out = String::new();
    for (node, row) in &m.cells {
        for (atom, cell) in row.iter().filter(|(_, c)| **c != Cell::Denied) {
            let _ = writeln!(out, "{node} {atom} {}", cell.as_str());
        }
    }
    out
}

/// How many cells of each kind the matrix holds.
pub fn census(m: &Matrix) -> BTreeMap<Cell, usize> {
    let mut counts = BTreeMap::new();
    for cell in m.cells.values().flat_map(BTreeMap::values) {
        *counts.entry(*cell).or_insert(0) += 1;
    }
    tracing::info!(kinds = counts.len(), "capability census taken");
    counts
}
