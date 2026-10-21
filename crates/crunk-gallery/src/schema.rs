//! The shipped JSON Schemas of the gallery manifest (v1 to v3) and of the `check --json` report.

// frob:ticket 01M43ATDG0RG5DP9PVFAKETJJH

use serde_json::Value;

/// Gallery manifest schema, version 1 (screen-level approvals).
pub const MANIFEST_V1: &str = include_str!("../../../docs/schemas/crunk-gallery-manifest-v1.json");
/// Gallery manifest schema, version 2 (per-state cells, hashed render).
pub const MANIFEST_V2: &str = include_str!("../../../docs/schemas/crunk-gallery-manifest-v2.json");
/// Gallery manifest schema, version 3 (attributed, expiring verdicts).
pub const MANIFEST_V3: &str = include_str!("../../../docs/schemas/crunk-gallery-manifest-v3.json");
/// Schema of the `gallery check --json` report.
pub const CHECK_V1: &str = include_str!("../../../docs/schemas/crunk-gallery-check-v1.json");

/// One schema violation and where in the document it is.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Located {
    /// JSON pointer to the offending value (empty for the document root).
    pub pointer: String,
    /// What is wrong there.
    pub message: String,
}

/// The manifest schema text of `version`, or `None` for an unknown version.
pub fn manifest_schema(version: u64) -> Option<&'static str> {
    match version {
        1 => Some(MANIFEST_V1),
        2 => Some(MANIFEST_V2),
        3 => Some(MANIFEST_V3),
        _ => None,
    }
}

/// Every violation of `instance` against the schema text `schema`, each with its JSON pointer.
///
/// # Panics
///
/// When `schema` is not a valid schema: the shipped schemas are tested to compile.
pub fn validate(schema: &str, instance: &Value) -> Vec<Located> {
    let schema: Value = serde_json::from_str(schema).expect("shipped schema is JSON");
    let validator = jsonschema::validator_for(&schema).expect("shipped schema compiles");
    let found: Vec<Located> = validator
        .iter_errors(instance)
        .map(|e| Located {
            pointer: e.instance_path().to_string(),
            message: e.to_string(),
        })
        .collect();
    tracing::debug!(violations = found.len(), "gallery schema validation");
    found
}
