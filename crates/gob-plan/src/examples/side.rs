//! The side tables an example supplies: `diff`, `lease` and `config` inputs as typed rows.
//!
//! `config` text is read as the small TOML subset the corpus writes: `[table]` and `[[array]]`
//! headers and `key = value` lines with string, integer, boolean or string-array values.

// frob:ticket 01M4XJMM949EHC6X13TYJPYE5V
use crate::catalog::{Column, FieldType};
use crate::exec::Scalar;
use crate::exec::relations::{SideData, SideTable};
use crate::plan::{Op, Plan};

use super::model_reader::read_model;
use super::runner::RunError;

/// The status column value of every example `diff` path.
const EXAMPLE_STATUS: &str = "modified";
/// The ticket an example `lease` is held for.
const EXAMPLE_TICKET: (&str, &str) = ("01EXAMPLE", "~EXAMPLE");

fn col(name: &str, ty: FieldType) -> Column {
    Column {
        name: name.to_owned(),
        ty,
    }
}

fn s(v: &str) -> Scalar {
    Scalar::Str(v.to_owned())
}

/// What an example wrote besides its files.
#[derive(Debug, Default, PartialEq, Eq)]
pub(crate) struct SideInputs {
    /// The `config` TOML text.
    pub(crate) config: Option<String>,
    /// The `diff` paths, when the example has a `diff` input.
    pub(crate) diff: Option<Vec<String>>,
    /// The `lease` globs, when the example has a `lease` input.
    pub(crate) lease: Option<Vec<String>>,
    /// The `model` text (grmb), read into `model.nodes` and `model.selectors`.
    pub(crate) model: Option<String>,
}

/// One parsed config value.
fn value(raw: &str) -> Option<Scalar> {
    let raw = raw.trim();
    if let Some(inner) = raw.strip_prefix('"').and_then(|r| r.strip_suffix('"')) {
        return Some(s(inner));
    }
    match raw {
        "true" => Some(Scalar::Bool(true)),
        "false" => Some(Scalar::Bool(false)),
        _ => raw.parse().ok().map(Scalar::Int),
    }
}

fn ty_of(v: &Scalar) -> FieldType {
    match v {
        Scalar::Str(_) => FieldType::Str,
        Scalar::Int(_) => FieldType::Int,
        Scalar::Bool(_) => FieldType::Bool,
    }
}

/// The `model.nodes` and `model.selectors` tables of an example's grmb `model` text.
///
/// # Errors
/// [`RunError::Model`] when the installed reader refuses the text.
fn model_tables(text: &str) -> Result<[(&'static str, SideTable); 2], RunError> {
    let rows = read_model(text)
        .map_err(|e| RunError::Model(format!("the example `model` does not parse: {e}")))?;
    let mut nodes = Vec::new();
    let mut selectors = Vec::new();
    for row in &rows {
        nodes.push(vec![s(&row.name), s(&row.kind), s(&row.path)]);
        selectors.extend(row.selectors.iter().map(|sel| vec![s(&row.name), s(sel)]));
    }
    tracing::debug!(
        nodes = nodes.len(),
        selectors = selectors.len(),
        "example model read"
    );
    let node_cols = vec![
        col("name", FieldType::Str),
        col("kind", FieldType::Str),
        col("path", FieldType::Str),
    ];
    let sel_cols = vec![col("node", FieldType::Str), col("selector", FieldType::Str)];
    Ok([
        ("model.nodes", SideTable::new(node_cols, nodes)),
        ("model.selectors", SideTable::new(sel_cols, selectors)),
    ])
}

/// A config table under construction: its rows as `(key, value)` pairs.
type Rows = Vec<Vec<(String, Scalar)>>;

/// Reads the config subset into `config.<path>` tables: an array of strings is a one-column
/// (`value`) table, an `[[array]]` header starts a row of keyed columns.
fn config_tables(text: &str) -> Result<Vec<(String, SideTable)>, RunError> {
    let bad = |line: &str| RunError::Model(format!("unsupported config line `{line}`"));
    let mut out: Vec<(String, Rows)> = Vec::new();
    let mut section = String::new();
    for line in text.lines().map(str::trim).filter(|l| !l.is_empty()) {
        if line.starts_with('#') {
            continue;
        }
        if let Some(h) = line.strip_prefix("[[").and_then(|l| l.strip_suffix("]]")) {
            h.trim().clone_into(&mut section);
            let name = format!("config.{section}");
            match out.iter_mut().find(|(n, _)| *n == name) {
                Some((_, rows)) => rows.push(Vec::new()),
                None => out.push((name, vec![Vec::new()])),
            }
        } else if let Some(h) = line.strip_prefix('[').and_then(|l| l.strip_suffix(']')) {
            h.trim().clone_into(&mut section);
        } else {
            let (key, raw) = line.split_once('=').ok_or_else(|| bad(line))?;
            let key = key.trim();
            if let Some(items) = raw
                .trim()
                .strip_prefix('[')
                .and_then(|r| r.strip_suffix(']'))
            {
                let rows = items
                    .split(',')
                    .filter(|i| !i.trim().is_empty())
                    .map(|i| value(i).map(|v| vec![("value".to_owned(), v)]))
                    .collect::<Option<Rows>>()
                    .ok_or_else(|| bad(line))?;
                let path = if section.is_empty() {
                    key.to_owned()
                } else {
                    format!("{section}.{key}")
                };
                out.push((format!("config.{path}"), rows));
            } else {
                let v = value(raw).ok_or_else(|| bad(line))?;
                let name = format!("config.{section}");
                match out.iter_mut().find(|(n, _)| *n == name) {
                    Some((_, rows)) if !rows.is_empty() => {
                        rows.last_mut()
                            .expect("non-empty")
                            .push((key.to_owned(), v));
                    }
                    Some((_, rows)) => rows.push(vec![(key.to_owned(), v)]),
                    None => out.push((name, vec![vec![(key.to_owned(), v)]])),
                }
            }
        }
    }
    Ok(out
        .into_iter()
        .map(|(name, rows)| {
            let mut columns: Vec<Column> = Vec::new();
            for (k, v) in rows.iter().flatten() {
                if !columns.iter().any(|c| c.name == *k) {
                    columns.push(col(k, ty_of(v)));
                }
            }
            let cells = rows
                .iter()
                .map(|r| {
                    columns
                        .iter()
                        .map(|c| {
                            r.iter()
                                .find(|(k, _)| *k == c.name)
                                .map_or_else(|| s(""), |(_, v)| v.clone())
                        })
                        .collect()
                })
                .collect();
            (name, SideTable::new(columns, cells))
        })
        .collect())
}

/// The `config.` tables the plan names, so a table the example never wrote can be empty.
fn named_config_tables(plan: &Plan) -> Vec<(String, bool)> {
    let p = plan.parts();
    p.ops
        .iter()
        .filter_map(|op| match op {
            Op::FindSide { table, .. } => Some((*table, false)),
            Op::MatchGlobSet { table, .. } => Some((*table, true)),
            _ => None,
        })
        .map(|(t, glob)| (p.strings[t as usize].clone(), glob))
        .filter(|(n, _)| n.starts_with("config."))
        .collect()
}

/// Builds the side tables of one example for `plan`; a `config.` table the plan names but the
/// example does not write is supplied empty (the config default).
///
/// # Errors
/// [`RunError::Model`] when the config text or a table is not accepted.
pub(crate) fn side_data(plan: &Plan, inputs: &SideInputs) -> Result<SideData, RunError> {
    let refuse = |e: crate::exec::relations::SideError| RunError::Model(e.to_string());
    let mut side = SideData::new();
    if let Some(paths) = &inputs.diff {
        let rows = paths
            .iter()
            .map(|p| vec![s(p), s(EXAMPLE_STATUS)])
            .collect();
        let cols = vec![col("path", FieldType::Str), col("status", FieldType::Str)];
        side.insert("diff.changed", SideTable::new(cols, rows))
            .map_err(refuse)?;
    }
    if let Some(globs) = &inputs.lease {
        let rows = globs.iter().map(|g| vec![s(g)]).collect();
        side.insert(
            "lease.globs",
            SideTable::new(vec![col("glob", FieldType::Str)], rows),
        )
        .map_err(refuse)?;
        let cols = vec![col("id", FieldType::Str), col("handle", FieldType::Str)];
        let row = vec![s(EXAMPLE_TICKET.0), s(EXAMPLE_TICKET.1)];
        side.insert("lease.ticket", SideTable::new(cols, vec![row]))
            .map_err(refuse)?;
    }
    if let Some(text) = &inputs.model {
        for (name, t) in model_tables(text)? {
            side.insert(name, t).map_err(refuse)?;
        }
    }
    let mut written = Vec::new();
    if let Some(text) = &inputs.config {
        for (name, t) in config_tables(text)? {
            written.push(name.clone());
            side.insert(&name, t).map_err(refuse)?;
        }
    }
    for (name, glob) in named_config_tables(plan) {
        if !written.contains(&name) {
            let cols = if glob {
                vec![col("value", FieldType::Str)]
            } else {
                Vec::new()
            };
            side.insert(&name, SideTable::new(cols, Vec::new()))
                .map_err(refuse)?;
            written.push(name);
        }
    }
    tracing::debug!(tables = written.len(), "example side data built");
    Ok(side)
}

#[cfg(test)]
mod model_tests {
    use super::model_tables;

    // frob:tests model_tables
    #[test]
    fn model_text_without_a_reader_is_refused() {
        let err = model_tables("node a {}").unwrap_err();
        assert!(err.to_string().contains("no model reader"));
    }
}
