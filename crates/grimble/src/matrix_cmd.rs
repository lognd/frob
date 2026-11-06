//! `matrix`: the capability matrix (`docs/design/grimble/binding.md` section 7) as text, with its census.
//!
//! The cells come from `grimble_bind::caps::grant_cells` through the binding (`GrimbleRun::cells`):
//! grant cells plus the CAP001 `undeclared` and `unknown` ones. `uses` cells raise no finding and
//! were never printed, so they are left out. [`grimble_capabilities::output`] renders and counts.

// frob:ticket 01M5A75BY0FCJY0YXHRN8ZASNE

use std::collections::BTreeMap;

use gob_cli::{CliError, Command, Context, Outcome, Payload};
use grimble_bind::caps::GrantCell;
use grimble_capabilities::{Cell, Matrix, output};
use grimble_check::CheckOptions;
use schemars::JsonSchema;
use serde::Serialize;

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
    /// Always 0: cells come from the binding, so no finding goes unattributed (kept for schema stability).
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
        let matrix = matrix_of(&run.cells);
        let data = to_data(&matrix);
        tracing::info!(cells = data.cells.len(), "matrix printed");
        let mut lines: Vec<String> = output::render(&matrix).lines().map(str::to_owned).collect();
        lines.extend(data.census.iter().map(|(k, n)| format!("{k}: {n}")));
        Ok(Payload::new(data).with_rendered(lines))
    }
}

fn to_data(m: &Matrix) -> MatrixData {
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
        // Cells come from the binding, not from findings, so none is left unattributed.
        unattributed: 0,
    }
}

/// Fold the binding's grant cells into a matrix; `Uses` cells raise no finding so are left out.
pub fn matrix_of(cells: &[GrantCell]) -> Matrix {
    let mut matrix = Matrix::default();
    for c in cells.iter().filter(|c| c.cell != Cell::Uses) {
        let slot = matrix
            .cells
            .entry(c.node.clone())
            .or_default()
            .entry(c.atom.clone())
            .or_insert(c.cell);
        // A definite cell outranks `unknown` when one atom is reported both ways.
        if *slot == Cell::Unknown {
            *slot = c.cell;
        }
    }
    tracing::debug!(
        cells = cells.len(),
        nodes = matrix.cells.len(),
        "matrix folded from binding cells"
    );
    matrix
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cell(node: &str, atom: &str, cell: Cell) -> GrantCell {
        GrantCell {
            node: node.to_owned(),
            atom: atom.to_owned(),
            written: atom.to_owned(),
            file: "m.grmb".to_owned(),
            span: (1, 9),
            cell,
        }
    }

    fn cells() -> Vec<GrantCell> {
        vec![
            cell("node/a", "clock", Cell::Undeclared),
            cell("node/a", "fs.write", Cell::DeclaredUnused),
            cell("node/a", "net.connect", Cell::Unknown),
            cell("node/a", "fs.read", Cell::Uses),
        ]
    }

    // frob:ticket 01M6FY2A9F2KGF95BSR4M81218
    // frob:tests crates/grimble/src/matrix_cmd.rs::matrix_of
    #[test]
    fn matrix_reads_binding_cells() {
        let m = matrix_of(&cells());
        assert_eq!(
            output::render(&m),
            "node/a clock undeclared\nnode/a fs.write declared-unused\nnode/a net.connect unknown\n"
        );
    }

    // frob:tests crates/grimble/src/matrix_cmd.rs::matrix_of
    #[test]
    fn a_definite_cell_outranks_unknown_for_one_atom() {
        let m = matrix_of(&[
            cell("node/a", "clock", Cell::Unknown),
            cell("node/a", "clock", Cell::Undeclared),
        ]);
        assert_eq!(output::render(&m), "node/a clock undeclared\n");
    }

    // frob:tests crates/grimble/src/matrix_cmd.rs::to_data
    #[test]
    fn census_counts_each_kind() {
        let data = to_data(&matrix_of(&cells()));
        assert_eq!(data.cells.len(), 3);
        assert_eq!(data.census.get("undeclared"), Some(&1));
        assert_eq!(data.census.get("unknown"), Some(&1));
    }
}
