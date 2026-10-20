//! GitHub schema validation (mirror.md 3.6): the mapping is checked against the repository's
//! labels, issue types and project fields before any write.
//!
//! A run that names something the repository lacks fails once, with one diagnostic listing every
//! missing item and a remedy. Project fields other than status are read-time only.

// frob:ticket 01M4052R4AEFJ2MQ2H9A9X0DN3

use std::collections::{BTreeMap, BTreeSet};

use thiserror::Error;
use tracing::{debug, warn};

use crate::config::{MappingConfig, Route};

/// The one managed label every mirrored issue carries.
pub const MANAGED_LABEL: &str = "frob:managed";

/// The project field the mirror may write.
pub const STATUS_FIELD: &str = "Status";

/// What the repository offers, read once at the start of a run.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct RepoSchema {
    /// Label names.
    pub labels: BTreeSet<String>,
    /// Issue type names.
    pub issue_types: BTreeSet<String>,
    /// Project field names.
    pub project_fields: BTreeSet<String>,
}

/// Whether the mirror may change a project field.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FieldAccess {
    /// Read and reconciled back (status only).
    ReadWrite,
    /// Read at read time and never written.
    ReadOnly,
}

/// Access the mirror has to a project field: only status is writable.
pub fn project_field_access(name: &str) -> FieldAccess {
    if name == STATUS_FIELD {
        FieldAccess::ReadWrite
    } else {
        FieldAccess::ReadOnly
    }
}

/// The mapping names things the repository does not have (MIR001); nothing was written.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
#[error("MIR001 schema-missing: {}; remedy: create them in the repository or edit the mapping, then rerun", .missing.join(", "))]
pub struct SchemaError {
    /// Every missing item, as `kind name`.
    pub missing: Vec<String>,
}

/// Check `cfg` against `schema` before any write.
///
/// `values` maps a projection field to the values the run will route (for label prefixes and
/// issue types). The managed label, every routed label, issue type and custom field must exist.
///
/// # Errors
/// One [`SchemaError`] listing everything missing.
pub fn validate(
    cfg: &MappingConfig,
    values: &BTreeMap<String, Vec<String>>,
    schema: &RepoSchema,
) -> Result<(), SchemaError> {
    let mut missing = Vec::new();
    if !schema.labels.contains(MANAGED_LABEL) {
        missing.push(format!("label {MANAGED_LABEL}"));
    }
    for (field, route) in &cfg.fields {
        let vals = values.get(field).map_or(&[][..], Vec::as_slice);
        match route {
            Route::Label { prefix } => {
                for v in vals {
                    let name = format!("{prefix}{v}");
                    if !schema.labels.contains(&name) {
                        missing.push(format!("label {name}"));
                    }
                }
            }
            Route::IssueType => {
                for v in vals.iter().filter(|v| !schema.issue_types.contains(*v)) {
                    missing.push(format!("issue type {v}"));
                }
            }
            Route::Field { name } if !schema.project_fields.contains(name) => {
                missing.push(format!("project field {name}"));
            }
            Route::Field { .. } | Route::State | Route::Drop => {}
        }
    }
    missing.sort();
    missing.dedup();
    if missing.is_empty() {
        debug!("schema: mapping matches the repository");
        Ok(())
    } else {
        warn!(count = missing.len(), "schema: mapping names missing items");
        Err(SchemaError { missing })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cfg(route: Route) -> MappingConfig {
        MappingConfig {
            version: 1,
            fields: BTreeMap::from([("priority".to_owned(), route)]),
        }
    }

    fn schema(labels: &[&str]) -> RepoSchema {
        RepoSchema {
            labels: labels.iter().map(|s| (*s).to_owned()).collect(),
            ..RepoSchema::default()
        }
    }

    // frob:tests validate
    #[test]
    fn missing_label_fails_once_with_one_diagnostic_and_remedy() {
        let c = cfg(Route::Label {
            prefix: "priority:".into(),
        });
        let values = BTreeMap::from([("priority".to_owned(), vec!["high".into(), "low".into()])]);
        let err = validate(&c, &values, &schema(&[MANAGED_LABEL])).unwrap_err();
        assert_eq!(err.missing, ["label priority:high", "label priority:low"]);
        let text = err.to_string();
        assert!(text.contains("MIR001") && text.contains("remedy"));
        assert!(
            validate(
                &c,
                &values,
                &schema(&[MANAGED_LABEL, "priority:high", "priority:low"])
            )
            .is_ok()
        );
    }

    // frob:tests project_field_access
    #[test]
    fn only_status_project_field_is_written() {
        assert_eq!(project_field_access("Status"), FieldAccess::ReadWrite);
        assert_eq!(project_field_access("Iteration"), FieldAccess::ReadOnly);
        assert_eq!(project_field_access("Priority"), FieldAccess::ReadOnly);
    }
}
