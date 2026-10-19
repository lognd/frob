//! `CFG001`: a materialized knob is absent from the product file.

use std::path::Path;

use gob_rules::{Finding, RuleDecl, Severity};

use crate::describe::TableDescription;
use crate::error::ConfigError;
use crate::load::{lookup, read_table};
use crate::rules::cfg001::Cfg001;

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
    let rule = Cfg001::DEF
        .id
        .parse::<gob_rules::RuleId>()
        .unwrap_or_else(|e| unreachable!("declaration validates the id: {e}"));
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
