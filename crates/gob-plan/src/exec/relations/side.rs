//! Typed side relations: rows supplied by tools outside the code model (grl-spec.md section 6).
//!
//! `diff.changed`, `diff.added`, `lease.globs`, `lease.ticket`, `model.nodes` and
//! `model.selectors` have fixed columns in the catalog; a table supplied under one of those
//! names must match them exactly. `config.<table>` rows take whatever columns the caller types.
//! A `find p: diff.changed` binds `p` to each row in the order supplied, and `p.path` reads the
//! column.

use std::collections::BTreeMap;

use crate::catalog::{Column, FieldType, side_relation};
use crate::plan::StrId;

use super::super::core::{Datum, Scalar};

/// Why a side table was refused.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[non_exhaustive]
pub enum SideError {
    /// The name is not a fixed side relation and not under `config.`.
    #[error("`{name}` is not a side relation (fixed relations and `config.<table>` only)")]
    UnknownRelation {
        /// The name supplied.
        name: String,
    },
    /// The columns differ from the catalog's for a fixed relation.
    #[error("`{name}` must have columns {want}, got {got}")]
    WrongColumns {
        /// The relation.
        name: String,
        /// The catalog's columns, rendered.
        want: String,
        /// The supplied columns, rendered.
        got: String,
    },
    /// A row has the wrong width or a value of the wrong type.
    #[error("`{name}` row {row}: {why}")]
    BadRow {
        /// The relation.
        name: String,
        /// The row index.
        row: usize,
        /// What is wrong.
        why: String,
    },
}

/// One side table: typed columns and rows of scalars.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SideTable {
    columns: Vec<Column>,
    rows: Vec<Vec<Scalar>>,
}

impl SideTable {
    /// A table with `columns` and `rows`; row values are checked against the column types when
    /// the table is inserted into [`SideData`].
    pub fn new(columns: Vec<Column>, rows: Vec<Vec<Scalar>>) -> Self {
        Self { columns, rows }
    }

    /// The table's columns.
    pub fn columns(&self) -> &[Column] {
        &self.columns
    }

    /// The number of rows.
    pub fn len(&self) -> usize {
        self.rows.len()
    }

    /// Whether the table has no rows.
    pub fn is_empty(&self) -> bool {
        self.rows.is_empty()
    }

    /// The value of column `name` in row `row`, or [`Datum::Absent`] when there is no such
    /// column (a row has no field it does not declare).
    pub(crate) fn cell(&self, row: u32, name: &str) -> Datum {
        let Some(col) = self.columns.iter().position(|c| c.name == name) else {
            return Datum::Absent;
        };
        self.rows
            .get(row as usize)
            .and_then(|r| r.get(col))
            .map_or(Datum::Absent, |s| Datum::Known(s.clone()))
    }
}

/// A binding to one row of a side table: the table's name (plan string) and the row index.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct SideRow {
    /// The relation name as a plan string id.
    pub table: StrId,
    /// The row index in supply order.
    pub index: u32,
}

/// The side tables of a run, by dotted name.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct SideData {
    tables: BTreeMap<String, SideTable>,
}

fn accepts(ty: FieldType, v: &Scalar) -> bool {
    matches!(
        (ty, v),
        (FieldType::Str | FieldType::Glob, Scalar::Str(_))
            | (FieldType::Int | FieldType::Float, Scalar::Int(_))
            | (FieldType::Bool, Scalar::Bool(_))
            | (FieldType::Any, _)
    )
}

fn render(cols: &[Column]) -> String {
    let items: Vec<String> = cols
        .iter()
        .map(|c| format!("{}: {}", c.name, c.ty.name()))
        .collect();
    format!("({})", items.join(", "))
}

impl SideData {
    /// No tables.
    pub fn new() -> Self {
        Self::default()
    }

    /// Supplies `table` as `name`.
    ///
    /// # Errors
    /// [`SideError`] when `name` is neither a fixed relation nor under `config.`, when a fixed
    /// relation's columns differ from the catalog's, or when a row does not fit its columns.
    pub fn insert(&mut self, name: &str, table: SideTable) -> Result<(), SideError> {
        match side_relation(name) {
            Some(fixed) => {
                let want = fixed.typed_columns();
                if want != table.columns {
                    return Err(SideError::WrongColumns {
                        name: name.to_owned(),
                        want: render(&want),
                        got: render(&table.columns),
                    });
                }
            }
            None if name.starts_with("config.") => {}
            None => {
                return Err(SideError::UnknownRelation {
                    name: name.to_owned(),
                });
            }
        }
        for (i, row) in table.rows.iter().enumerate() {
            let bad = |why: String| SideError::BadRow {
                name: name.to_owned(),
                row: i,
                why,
            };
            if row.len() != table.columns.len() {
                return Err(bad(format!(
                    "{} values for {} columns",
                    row.len(),
                    table.columns.len()
                )));
            }
            if let Some((c, _)) = table
                .columns
                .iter()
                .zip(row)
                .find(|(c, v)| !accepts(c.ty, v))
            {
                return Err(bad(format!("column `{}` expects {}", c.name, c.ty.name())));
            }
        }
        tracing::debug!(name, rows = table.rows.len(), "side table supplied");
        self.tables.insert(name.to_owned(), table);
        Ok(())
    }

    /// The table supplied as `name`.
    pub fn get(&self, name: &str) -> Option<&SideTable> {
        self.tables.get(name)
    }
}
