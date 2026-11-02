//! `matrix`: the capability matrix (`docs/design/grimble/binding.md` section 7) as text, with its census.
//!
//! The cells come from the CAP findings of the `gob.sibling/1` document: a CAP001 error is an
//! `undeclared` cell, a CAP001 unresolved site an `unknown` cell, a CAP002 finding a
//! `declared-unused` cell and a CAP002 unresolved site an `unknown` cell. The node is the entity
//! whose file and byte range contain the finding's (CAP001 sits on the node, CAP002 on its grant); the atom is the first backticked name in the
//! message other than the node. Cells that raise no finding (`uses`, `denied`, `excused`) are not
//! in the document, so they are not printed. [`grimble_capabilities::output`] renders and counts.

// frob:ticket 01M5A75BY0FCJY0YXHRN8ZASNE

use std::collections::BTreeMap;

use gob_cli::{CliError, Command, Context, Outcome, Payload};
use grimble_capabilities::{Cell, Matrix, output};
use grimble_check::{CheckOptions, sibling_document};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::Value;

use crate::workspace::{check_error, locate_root};

/// Print the capability matrix and how many cells of each kind it holds.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "matrix",
    product = "grimble",
    idempotent = true,
    exits(ok, usage, internal)
)]
pub struct MatrixVerb;

/// One non-`denied` cell.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CellRow {
    /// The node anchor.
    pub node: String,
    /// The capability atom.
    pub atom: String,
    /// The cell spelling (`undeclared`, `declared-unused`, `unknown`).
    pub cell: String,
}

/// Output of `matrix`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct MatrixData {
    /// The cells, sorted by node then atom.
    pub cells: Vec<CellRow>,
    /// Cell spelling to how many cells of that kind.
    pub census: BTreeMap<String, usize>,
    /// CAP findings that matched no node or named no atom, so are not in `cells`.
    pub unattributed: usize,
}

impl Command for MatrixVerb {
    type Data = MatrixData;

    fn from_matches(_matches: &gob_cli::clap::ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<MatrixData> {
        let root = locate_root(&ctx.cwd);
        // Read-only view: leave no telemetry or precision history behind.
        let options = CheckOptions {
            skip_telemetry: true,
            ..CheckOptions::default()
        };
        let run = grimble_check::run(&root, &options).map_err(check_error)?;
        let (matrix, unattributed) = matrix_of(&sibling_document(&run));
        let data = to_data(&matrix, unattributed);
        tracing::info!(cells = data.cells.len(), unattributed, "matrix printed");
        let mut lines: Vec<String> = output::render(&matrix).lines().map(str::to_owned).collect();
        lines.extend(data.census.iter().map(|(k, n)| format!("{k}: {n}")));
        Ok(Payload::new(data).with_rendered(lines))
    }
}

fn to_data(m: &Matrix, unattributed: usize) -> MatrixData {
    let cells = m
        .cells
        .iter()
        .flat_map(|(node, row)| {
            row.iter()
                .filter(|(_, c)| **c != Cell::Denied)
                .map(|(atom, c)| CellRow {
                    node: node.clone(),
                    atom: atom.clone(),
                    cell: c.as_str().to_owned(),
                })
        })
        .collect();
    let census = output::census(m)
        .into_iter()
        .map(|(c, n)| (c.as_str().to_owned(), n))
        .collect();
    MatrixData {
        cells,
        census,
        unattributed,
    }
}

fn cell_of(rule: &str, severity: &str) -> Option<Cell> {
    match (rule, severity) {
        ("CAP001", "error") => Some(Cell::Undeclared),
        ("CAP001" | "CAP002", "unresolved") => Some(Cell::Unknown),
        ("CAP002", _) => Some(Cell::DeclaredUnused),
        _ => None,
    }
}

fn str_of<'a>(row: &'a Value, key: &str) -> &'a str {
    row.get(key).and_then(Value::as_str).unwrap_or_default()
}

/// A `(file, start, end)` byte range in a file.
type Site = (String, u64, u64);

/// The range a finding or an entity row occupies.
fn site_of(row: &Value) -> Option<Site> {
    let range = row.get("range")?;
    Some((
        str_of(row, "file").to_owned(),
        range.get("start")?.as_u64()?,
        range.get("end")?.as_u64()?,
    ))
}

/// The anchor of the narrowest node whose file and range contain `site`.
fn node_at<'a>(nodes: &'a [(Site, String)], site: &Site) -> Option<&'a String> {
    nodes
        .iter()
        .filter(|((file, start, end), _)| *file == site.0 && *start <= site.1 && site.2 <= *end)
        .min_by_key(|((_, start, end), _)| end - start)
        .map(|(_, anchor)| anchor)
}

/// The first backticked name in `message` that is not `node`.
fn atom_of(message: &str, node: &str) -> Option<String> {
    message
        .split('`')
        .skip(1)
        .step_by(2)
        .find(|t| !t.is_empty() && *t != node)
        .map(str::to_owned)
}

/// Fold the CAP findings of a `gob.sibling/1` document into a matrix, and count those left out.
pub fn matrix_of(doc: &Value) -> (Matrix, usize) {
    let nodes: Vec<(Site, String)> = doc["entities"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|e| str_of(e, "kind") == "node")
        .filter_map(|e| Some((site_of(e)?, str_of(e, "anchor").to_owned())))
        .collect();
    let mut matrix = Matrix::default();
    let mut unattributed = 0;
    for f in doc["findings"].as_array().into_iter().flatten() {
        let Some(cell) = cell_of(str_of(f, "rule"), str_of(f, "severity")) else {
            continue;
        };
        let node = site_of(f).and_then(|s| node_at(&nodes, &s));
        let atom = node.and_then(|n| atom_of(str_of(f, "message"), n));
        let (Some(node), Some(atom)) = (node, atom) else {
            tracing::warn!(
                rule = str_of(f, "rule"),
                "CAP finding has no node or atom; not in the matrix"
            );
            unattributed += 1;
            continue;
        };
        let slot = matrix
            .cells
            .entry(node.clone())
            .or_default()
            .entry(atom)
            .or_insert(cell);
        // A definite cell outranks `unknown` when one atom is reported both ways.
        if *slot == Cell::Unknown {
            *slot = cell;
        }
    }
    (matrix, unattributed)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn doc() -> Value {
        json!({
            "entities": [{"kind": "node", "anchor": "node/a", "file": "m.grmb", "range": {"start": 1, "end": 9}}],
            "findings": [
                {"rule": "CAP001", "severity": "error", "file": "m.grmb", "range": {"start": 1, "end": 9},
                 "message": "`node/a` uses `clock` with no grant (2 use(s))"},
                {"rule": "CAP002", "severity": "error", "file": "m.grmb", "range": {"start": 1, "end": 9},
                 "message": "`node/a` grants `fs.write` but no use"},
                {"rule": "CAP001", "severity": "unresolved", "file": "m.grmb", "range": {"start": 1, "end": 9},
                 "message": "`net.connect` may be used by `node/a` with no grant"},
                {"rule": "CAP001", "severity": "error", "file": "other.grmb", "range": {"start": 1, "end": 9},
                 "message": "`unowned` stray"},
                {"rule": "SYS001", "severity": "error", "file": "m.grmb", "range": {"start": 1, "end": 9},
                 "message": "`x`"}
            ]
        })
    }

    // frob:tests crates/grimble/src/matrix_cmd.rs::matrix_of
    #[test]
    fn cells_come_from_cap_findings() {
        let (m, unattributed) = matrix_of(&doc());
        assert_eq!(unattributed, 1);
        let text = output::render(&m);
        assert_eq!(
            text,
            "node/a clock undeclared\nnode/a fs.write declared-unused\nnode/a net.connect unknown\n"
        );
    }

    // frob:tests crates/grimble/src/matrix_cmd.rs::to_data
    #[test]
    fn census_counts_each_kind() {
        let (m, unattributed) = matrix_of(&doc());
        let data = to_data(&m, unattributed);
        assert_eq!(data.cells.len(), 3);
        assert_eq!(data.census.get("undeclared"), Some(&1));
        assert_eq!(data.census.get("unknown"), Some(&1));
    }
}
