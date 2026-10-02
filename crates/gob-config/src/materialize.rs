//! Writing absent enforcement knobs with their defaults and docs.

use std::path::{Path, PathBuf};

use toml_edit::{DocumentMut, Item, Table, Value};

use crate::describe::{FieldDescription, TableDescription};
use crate::error::ConfigError;

/// What [`materialize`] did.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MaterializeReport {
    /// The config file written (or that would hold the knobs).
    pub path: PathBuf,
    /// Full dotted keys that were added, e.g. `tickets.cas_retries`.
    pub added: Vec<String>,
    /// True when the file did not exist and was created.
    pub created: bool,
}

/// Add every absent enforcement knob of the materialized `tables` to the file.
///
/// Existing values, comments and ordering are never touched; the file is
/// written only when something was added.
///
/// # Errors
///
/// `Io`/`Parse` for an unreadable or invalid file, `Invalid` when a table path
/// holds a non-table value.
pub fn materialize(
    root: &Path,
    product: &str,
    tables: &[&TableDescription],
) -> Result<MaterializeReport, ConfigError> {
    let path = crate::config_path(root, product);
    let (text, existed) = match std::fs::read_to_string(&path) {
        Ok(t) => (t, true),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => (String::new(), false),
        Err(source) => return Err(ConfigError::Io { path, source }),
    };
    let mut doc = text
        .parse::<DocumentMut>()
        .map_err(|e| ConfigError::Parse {
            path: path.clone(),
            message: e.to_string(),
        })?;
    let mut added = Vec::new();
    for desc in tables.iter().filter(|d| d.materialize) {
        let missing: Vec<&FieldDescription> = desc
            .fields
            .iter()
            .filter(|f| f.enforcement && !has_key(&doc, &desc.table, &f.key))
            .collect();
        if missing.is_empty() {
            continue;
        }
        let table = table_at(&mut doc, &desc.table)?;
        for field in missing {
            insert_knob(table, field, &desc.table)?;
            tracing::info!(table = %desc.table, key = %field.key, default = %field.default_toml, "materialized config knob");
            added.push(format!("{}.{}", desc.table, field.key));
        }
    }
    if !added.is_empty() {
        std::fs::write(&path, doc.to_string()).map_err(|source| ConfigError::Io {
            path: path.clone(),
            source,
        })?;
    }
    Ok(MaterializeReport {
        created: !existed && !added.is_empty(),
        path,
        added,
    })
}

fn has_key(doc: &DocumentMut, dotted: &str, key: &str) -> bool {
    dotted
        .split('.')
        .try_fold(doc.as_table(), |t, seg| t.get(seg)?.as_table())
        .is_some_and(|t| t.contains_key(key))
}

/// Find or create the table at a dotted path (parents stay implicit).
fn table_at<'d>(doc: &'d mut DocumentMut, dotted: &str) -> Result<&'d mut Table, ConfigError> {
    let segs: Vec<&str> = dotted.split('.').collect();
    let mut cur = doc.as_table_mut();
    for (i, seg) in segs.iter().enumerate() {
        let last = i + 1 == segs.len();
        if !cur.contains_key(seg) {
            let mut t = Table::new();
            t.set_implicit(!last);
            cur.insert(seg, Item::Table(t));
        }
        cur = cur
            .get_mut(seg)
            .and_then(Item::as_table_mut)
            .ok_or_else(|| ConfigError::Invalid {
                table: dotted.to_owned(),
                message: format!("`{seg}` is not a table"),
            })?;
    }
    Ok(cur)
}

fn insert_knob(
    table: &mut Table,
    field: &FieldDescription,
    dotted: &str,
) -> Result<(), ConfigError> {
    let value: Value = field
        .default_toml
        .parse()
        .map_err(|e: toml_edit::TomlError| ConfigError::Invalid {
            table: dotted.to_owned(),
            message: format!("default of `{}` is not valid TOML: {e}", field.key),
        })?;
    table.insert(&field.key, Item::Value(value));
    if let Some(mut key) = table.key_mut(&field.key) {
        let comment: String = field
            .doc
            .lines()
            .map(|l| {
                if l.is_empty() {
                    "#\n".to_owned()
                } else {
                    format!("# {l}\n")
                }
            })
            .collect();
        key.leaf_decor_mut().set_prefix(comment);
    }
    Ok(())
}
