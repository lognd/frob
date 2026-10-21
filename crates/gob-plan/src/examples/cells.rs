//! The `engine.cells` table behind the `cell` kind: one row per (node, atom) an example's code
//! uses, with whether the node grants it.
//!
//! A cell is observed when a call in the example's code names a callee of the atom's vocabulary in
//! the example's language (the shared registry, as `grimble-bind` reads it); the node is the model
//! node whose `owns` selector matches the example's file path. `granted` is a `may` clause of the
//! node naming the atom or an ancestor of it (`net` covers `net.listen`). `excused` is an
//! `excuses` clause of the node under the same rule. A `may ... at` grant is not read (it covers
//! only part of the node's code), and a grant's string arguments are ignored.

// frob:ticket 01M5ETB7SWJPH7EVK97WHEVEHY
use std::collections::BTreeSet;

use globset::Glob;
use gob_ir::{Answer, Model, Operator, Universal};
use gob_text::SourceText;

use super::model_reader::ModelNodeRow;
use crate::catalog::{Column, FieldType};
use crate::exec::Scalar;
use crate::exec::relations::SideTable;

/// The line recorded for a cell whose call has no readable source position.
const NO_LINE: i64 = 0;

fn col(name: &str, ty: FieldType) -> Column {
    Column {
        name: name.to_owned(),
        ty,
    }
}

/// The columns of `engine.cells`.
fn columns() -> Vec<Column> {
    vec![
        col("node", FieldType::Str),
        col("atom", FieldType::Str),
        col("observed", FieldType::Bool),
        col("granted", FieldType::Bool),
        col("excused", FieldType::Bool),
        col("line", FieldType::Int),
    ]
}

/// Whether the written `callee` names a vocabulary entry (a Rust path entry also matches behind
/// extra leading segments: `std::net::TcpListener::bind` names `TcpListener::bind`).
fn names_callee(lang: &str, names: &BTreeSet<&str>, callee: &str) -> bool {
    names.contains(callee)
        || (lang == "rust"
            && names
                .iter()
                .any(|n| n.contains("::") && callee.ends_with(&format!("::{n}"))))
}

/// Whether `grant` covers `atom`: the same atom or a dotted ancestor of it.
fn covers(grant: &str, atom: &str) -> bool {
    atom == grant
        || atom
            .strip_prefix(grant)
            .is_some_and(|rest| rest.starts_with('.'))
}

/// Whether any `owns` selector of `row` matches `path`; a selector that is not a glob owns nothing.
fn owns(row: &ModelNodeRow, path: &str) -> bool {
    row.selectors.iter().any(|sel| {
        let sel = sel.trim_matches('"');
        match Glob::new(sel) {
            Ok(g) => g.compile_matcher().is_match(path),
            Err(e) => {
                tracing::warn!(selector = sel, error = %e, "unreadable owns selector owns nothing");
                false
            }
        }
    })
}

/// The first line (and callee) of each distinct callee the model's calls name, in source order.
fn calls(model: &Model, source: &SourceText) -> Vec<(String, i64)> {
    let term = model.term();
    let mut out: Vec<(String, i64)> = Vec::new();
    for id in term.ids() {
        let n = term.node(id);
        if !matches!(n.op(), Operator::Universal(Universal::Apply { kind }) if kind == "call") {
            continue;
        }
        let Some(&head) = n.children().first() else {
            continue;
        };
        let Operator::Universal(Universal::Ref { name }) = term.node(head).op() else {
            continue;
        };
        let line = n
            .location()
            .span()
            .and_then(|s| source.line_col(s.range.start()))
            .map_or(NO_LINE, |lc| i64::from(lc.line));
        out.push((name.clone(), line));
    }
    out.sort_by_key(|(_, line)| *line);
    out
}

/// The `engine.cells` table of an example whose code `model` was read from `path` in `lang`, for
/// the model nodes `rows`. A file no node owns, or an empty model, yields an empty table.
///
/// frob:ticket 01M5ETB7SWJPH7EVK97WHEVEHY
pub(crate) fn cell_table(
    model: &Model,
    source: &SourceText,
    (path, lang): (Option<&str>, &str),
    rows: &[ModelNodeRow],
) -> SideTable {
    let owners: Vec<&ModelNodeRow> = path
        .map(|p| rows.iter().filter(|r| owns(r, p)).collect())
        .unwrap_or_default();
    let mut cells: Vec<Vec<Scalar>> = Vec::new();
    if !owners.is_empty() {
        let seen = calls(model, source);
        for atom in gob_ir::registry::atoms() {
            let Answer::Exact(names) = gob_ir::registry::callee_vocab(lang, atom.name) else {
                continue;
            };
            let Some((_, line)) = seen.iter().find(|(c, _)| names_callee(lang, &names, c)) else {
                continue;
            };
            for node in &owners {
                let granted = node.grants.iter().any(|g| covers(g, atom.name));
                let excused = node.excuses.iter().any(|g| covers(g, atom.name));
                cells.push(vec![
                    Scalar::Str(node.name.clone()),
                    Scalar::Str(atom.name.to_owned()),
                    Scalar::Bool(true),
                    Scalar::Bool(granted),
                    Scalar::Bool(excused),
                    Scalar::Int(*line),
                ]);
            }
        }
    }
    tracing::debug!(
        cells = cells.len(),
        owners = owners.len(),
        "engine cells built"
    );
    SideTable::new(columns(), cells)
}

#[cfg(test)]
mod tests {
    use super::{covers, names_callee};
    use std::collections::BTreeSet;

    // frob:tests covers
    #[test]
    fn a_grant_covers_its_atom_and_descendants() {
        assert!(covers("net.listen", "net.listen"));
        assert!(covers("net", "net.listen"));
        assert!(!covers("net", "network.x"));
        assert!(!covers("net.listen", "net"));
    }

    // frob:tests names_callee
    #[test]
    fn rust_paths_match_behind_leading_segments() {
        let names = BTreeSet::from(["TcpListener::bind"]);
        assert!(names_callee("rust", &names, "std::net::TcpListener::bind"));
        assert!(!names_callee(
            "python",
            &names,
            "std::net::TcpListener::bind"
        ));
        assert!(names_callee("python", &BTreeSet::from(["open"]), "open"));
    }
}
