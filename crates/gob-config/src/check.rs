//! `CFG001`: a materialized knob is absent from the product file.

use std::path::Path;

use gob_rules::{Finding, Rule, Severity};

use crate::describe::TableDescription;
use crate::error::ConfigError;
use crate::load::{lookup, read_table};

/// A materialized config knob is missing from the product config file.
///
/// Every knob that affects behavior must be written down with its default so
/// no variable is invisible; run `frob init` (or `frob config sync`) to add it.
#[derive(Debug, Clone, Copy, Default, gob_rules::Rule)]
#[rule(
    id = "CFG001",
    slug = "missing-materialized-knob",
    family = "CFG",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Deterministic,
    version = 1
)]
pub struct Cfg001;

/// One `CFG001` finding per enforcement knob of `tables` absent from the file.
///
/// A missing file counts as every knob missing.
///
/// # Errors
///
/// `Io`/`Parse` when the file exists but cannot be read or parsed.
pub fn check(
    root: &Path,
    product: &str,
    tables: &[&TableDescription],
) -> Result<Vec<Finding>, ConfigError> {
    let path = crate::config_path(root, product);
    let (doc, _) = read_table(&path)?;
    let file = format!("{product}.toml");
    let rule = Cfg001
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"));
    let mut findings = Vec::new();
    for desc in tables.iter().filter(|d| d.materialize) {
        let present = lookup(&doc, &desc.table);
        for field in desc.fields.iter().filter(|f| f.enforcement) {
            if present.is_some_and(|t| t.get(&field.key).is_some()) {
                continue;
            }
            let full = format!("{}.{}", desc.table, field.key);
            let message = format!(
                "missing materialized knob `{full}` in {file} (default {}); run `{product} init` (or `{product} config sync`) to write it",
                field.default_toml
            );
            tracing::debug!(key = %full, "CFG001");
            findings.push(Finding::new(
                rule.clone(),
                Severity::Error,
                None,
                message,
                &format!("{file}::{full}"),
            ));
        }
    }
    Ok(findings)
}
