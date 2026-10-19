//! The capability matrix of grimble-model.md 9.6: one cell per node and atom, and a summary
//! that carries one Unresolved per node whose cells include `unknown`.
//!
//! Cells come from the detector registry (`gob_ir::registry::detectors`): an atom with no
//! detector in a node's language is `unknown`, one whose detector declares the capability
//! impossible is `not-applicable`. Known limits: excuses are taken as an input set (template
//! matching and CAP004 are not here), and the CAP findings are still emitted by `grimble-bind`.

// frob:ticket 01M3Z714EEST9EGEHWWV56RXG4

use std::collections::{BTreeMap, BTreeSet};

use gob_ir::Answer;
use gob_ir::registry::detectors;

/// One cell of the matrix.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Cell {
    /// A use was observed and the atom is granted.
    Uses,
    /// A use was observed without a grant (CAP001).
    Undeclared,
    /// A grant without an observed use (CAP002).
    DeclaredUnused,
    /// No grant and no use: denied, no finding.
    Denied,
    /// A matrix-build excuse covers the node and no use was observed.
    Excused,
    /// The detector for this atom in this language is absent or answered Unknown.
    Unknown,
    /// The detector declares the capability impossible in this language.
    NotApplicable,
}

impl Cell {
    /// The spelling used in matrix output.
    pub fn as_str(self) -> &'static str {
        match self {
            Cell::Uses => "uses",
            Cell::Undeclared => "undeclared",
            Cell::DeclaredUnused => "declared-unused",
            Cell::Denied => "denied",
            Cell::Excused => "excused",
            Cell::Unknown => "unknown",
            Cell::NotApplicable => "not-applicable",
        }
    }
}

/// What the matrix needs to know about one node.
#[derive(Debug, Clone, Default)]
pub struct NodeInput {
    /// The node's name.
    pub node: String,
    /// The language of the code the node owns.
    pub lang: String,
    /// Atoms granted by the node's `may` clauses.
    pub grants: BTreeSet<String>,
    /// Atoms with an observed use in the node's code.
    pub uses: BTreeSet<String>,
    /// Atoms covered by a matrix-build excuse.
    pub excused: BTreeSet<String>,
}

/// One node's unknown cells, reported as a single Unresolved.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnresolvedNode {
    /// The node.
    pub node: String,
    /// The atoms whose cell is `unknown` for it.
    pub atoms: Vec<String>,
}

/// The built matrix and its summary.
#[derive(Debug, Clone, Default)]
pub struct Matrix {
    /// Cells keyed by node then atom.
    pub cells: BTreeMap<String, BTreeMap<String, Cell>>,
    /// One entry per node with at least one `unknown` cell.
    pub unresolved: Vec<UnresolvedNode>,
}

/// True when `grant` covers `atom` (equal, or a dotted ancestor: `fs` covers `fs.read`).
fn covers(grant: &str, atom: &str) -> bool {
    atom == grant || atom.strip_prefix(grant).is_some_and(|r| r.starts_with('.'))
}

/// The cell of `atom` for `node`.
fn cell_of(node: &NodeInput, atom: &str) -> Cell {
    match detectors(atom, &node.lang) {
        Answer::NotApplicable => return Cell::NotApplicable,
        Answer::Unknown => return Cell::Unknown,
        _ => {}
    }
    let granted = node.grants.iter().any(|g| covers(g, atom));
    let used = node.uses.iter().any(|u| covers(atom, u) || covers(u, atom));
    let excused = node.excused.iter().any(|e| covers(e, atom));
    match (used, granted, excused) {
        (true, true, _) => Cell::Uses,
        (true, false, _) => Cell::Undeclared,
        (false, _, true) => Cell::Excused,
        (false, true, false) => Cell::DeclaredUnused,
        (false, false, false) => Cell::Denied,
    }
}

/// Build the matrix for `nodes` over `atoms`; each node with unknown cells yields one Unresolved.
pub fn build(nodes: &[NodeInput], atoms: &[&str]) -> Matrix {
    let mut m = Matrix::default();
    for node in nodes {
        let row: BTreeMap<String, Cell> = atoms
            .iter()
            .map(|a| ((*a).to_owned(), cell_of(node, a)))
            .collect();
        let unknown: Vec<String> = row
            .iter()
            .filter(|(_, c)| **c == Cell::Unknown)
            .map(|(a, _)| a.clone())
            .collect();
        if !unknown.is_empty() {
            tracing::debug!(node = %node.node, lang = %node.lang, ?unknown, "unknown cells: one Unresolved");
            m.unresolved.push(UnresolvedNode {
                node: node.node.clone(),
                atoms: unknown,
            });
        }
        m.cells.insert(node.node.clone(), row);
    }
    tracing::info!(
        nodes = nodes.len(),
        unresolved = m.unresolved.len(),
        "capability matrix built"
    );
    m
}
