//! Layered loading: defaults < file < explicit overrides.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use crate::describe::{ConfigTable, TableDescription};
use crate::error::ConfigError;

/// Where one config table is read from, plus explicit (CLI) overrides.
#[derive(Debug, Clone)]
pub struct ConfigSource {
    /// The product config file; may be absent on disk.
    pub file: PathBuf,
    /// Overrides keyed by full dotted key, e.g. `tickets.cas_retries`.
    pub overrides: BTreeMap<String, toml::Value>,
}

impl ConfigSource {
    /// Source for `<root>/<product>.toml` with no overrides.
    pub fn new(root: &Path, product: &str) -> Self {
        Self {
            file: crate::config_path(root, product),
            overrides: BTreeMap::new(),
        }
    }
}

/// Which layer supplied a key's effective value.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Provenance {
    /// The declared default.
    Default,
    /// The product config file.
    File,
    /// An explicit override.
    Override,
}

/// A loaded table with provenance per key.
#[derive(Debug)]
pub struct Loaded<T> {
    /// The effective value.
    pub value: T,
    /// Whether the config file existed.
    pub file_present: bool,
    /// Layer of each key, by key name within the table.
    pub provenance: BTreeMap<String, Provenance>,
}

/// Load table `T` from `<root>/<product>.toml` (missing file means defaults).
///
/// # Errors
///
/// See [`load_with`].
pub fn load<T: ConfigTable>(root: &Path, product: &str) -> Result<Loaded<T>, ConfigError> {
    load_with(&ConfigSource::new(root, product))
}

/// Load table `T` from `source`, layering defaults < file < overrides.
///
/// # Errors
///
/// `Io`/`Parse` for an unreadable file, `UnknownKey` (with nearest-key
/// suggestion) for an undeclared key in the file or overrides, `Invalid` for a
/// wrong-shaped table or mistyped value.
pub fn load_with<T: ConfigTable>(source: &ConfigSource) -> Result<Loaded<T>, ConfigError> {
    let desc = T::describe();
    let (root, file_present) = read_table(&source.file)?;
    let mut merged = match lookup(&root, &desc.table) {
        Some(toml::Value::Table(t)) => t.clone(),
        Some(_) => {
            return Err(ConfigError::Invalid {
                table: desc.table,
                message: "expected a table".to_owned(),
            });
        }
        None => toml::Table::new(),
    };
    let mut provenance: BTreeMap<String, Provenance> = desc
        .fields
        .iter()
        .map(|f| (f.key.clone(), Provenance::Default))
        .collect();
    // Keys naming a nested table owned by another registered table are not ours.
    let child_prefix = format!("{}.", desc.table);
    merged.retain(|key, _| {
        let child = format!("{child_prefix}{key}");
        !crate::describe::all_tables()
            .any(|d| d.table == child || d.table.starts_with(&format!("{child}.")))
    });
    for key in merged.keys() {
        reject_unknown(&desc, key)?;
        provenance.insert(key.clone(), Provenance::File);
    }
    let prefix = format!("{}.", desc.table);
    for (full, value) in &source.overrides {
        if let Some(key) = full.strip_prefix(&prefix) {
            reject_unknown(&desc, key)?;
            merged.insert(key.to_owned(), value.clone());
            provenance.insert(key.to_owned(), Provenance::Override);
        }
    }
    tracing::debug!(table = %desc.table, file = %source.file.display(), file_present, "loading config table");
    let value = toml::Value::Table(merged)
        .try_into::<T>()
        .map_err(|e| ConfigError::Invalid {
            table: desc.table.clone(),
            message: e.to_string(),
        })?;
    Ok(Loaded {
        value,
        file_present,
        provenance,
    })
}

/// Read and parse a TOML file; a missing file yields an empty table.
pub(crate) fn read_table(path: &Path) -> Result<(toml::Value, bool), ConfigError> {
    match std::fs::read_to_string(path) {
        Ok(text) => {
            let table = text
                .parse::<toml::Table>()
                .map_err(|e| ConfigError::Parse {
                    path: path.to_owned(),
                    message: e.to_string(),
                })?;
            Ok((toml::Value::Table(table), true))
        }
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            tracing::debug!(file = %path.display(), "config file absent; using defaults");
            Ok((toml::Value::Table(toml::Table::new()), false))
        }
        Err(source) => Err(ConfigError::Io {
            path: path.to_owned(),
            source,
        }),
    }
}

/// Follow a dotted table path through nested tables.
pub(crate) fn lookup<'a>(root: &'a toml::Value, dotted: &str) -> Option<&'a toml::Value> {
    dotted.split('.').try_fold(root, |cur, seg| cur.get(seg))
}

fn reject_unknown(desc: &TableDescription, key: &str) -> Result<(), ConfigError> {
    if desc.fields.iter().any(|f| f.key == key) {
        return Ok(());
    }
    let suggestion = nearest(key, desc.fields.iter().map(|f| f.key.as_str()));
    tracing::warn!(table = %desc.table, key, ?suggestion, "unknown config key");
    Err(ConfigError::UnknownKey {
        table: desc.table.clone(),
        key: key.to_owned(),
        suggestion,
    })
}

/// The candidate with the smallest edit distance, if within a sane bound.
fn nearest<'a>(key: &str, candidates: impl Iterator<Item = &'a str>) -> Option<String> {
    let limit = (key.len() / 2).max(2);
    candidates
        .map(|c| (strsim::levenshtein(key, c), c))
        .filter(|(d, _)| *d <= limit)
        .min_by_key(|(d, _)| *d)
        .map(|(_, c)| c.to_owned())
}
