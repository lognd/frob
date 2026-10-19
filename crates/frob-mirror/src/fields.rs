//! Field ownership (mirror.md 3.4, 3.6): one owner per projected field, and a write type that
//! cannot name a tracker-owned field.
//!
//! In version 1 every field the mirror writes is repository-owned. Tracker-owned are comments,
//! reactions, labels outside the `frob:` namespace, fields listed in `tracker_owned`, and every
//! project field except `status`. A [`WriteOp`] can only be built through
//! [`FieldOwnership::authorize`], so an operation on a tracker-owned field is inexpressible.

// frob:ticket 01M4052SFS22HBR73HQN1E4FA4

use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};
use thiserror::Error;
use tracing::{debug, trace, warn};

use crate::mapping::PlannedOps;

/// The label namespace the mirror owns; every other label belongs to the tracker.
pub const MANAGED_LABEL_PREFIX: &str = "frob:";

/// The only project field the mirror reconciles (mirror.md 3.6).
pub const PROJECT_STATUS_FIELD: &str = "status";

/// Who owns a projected field.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Owner {
    /// The repository: the mirror writes it and reverts outside edits.
    Repository,
    /// The tracker: the mirror never writes it.
    Tracker,
}

/// The raw `[mirror.fields]` table.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FieldsConfig {
    /// Projection field name (`snake_case`) to its single owner.
    pub owners: BTreeMap<String, Owner>,
    /// Tracker-side custom field names the mirror must never write.
    #[serde(default)]
    pub tracker_owned: Vec<String>,
}

/// Why field ownership failed to load or a write was refused.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum FieldsError {
    /// A projected field has no owner in `[mirror.fields]`.
    #[error("projected field `{0}` has no owner in [mirror.fields]")]
    Unowned(String),
    /// `[mirror.fields]` names a field that is not projected.
    #[error("[mirror.fields] names unknown field `{0}`")]
    Unknown(String),
    /// The target is tracker-owned, so the mirror must not write it.
    #[error("`{target}` is tracker-owned and is never written")]
    TrackerOwned {
        /// The refused target.
        target: String,
    },
    /// A project field other than `status` was targeted.
    #[error("project field `{0}` is read-only (only `status` is reconciled)")]
    ProjectFieldReadOnly(String),
}

/// Where a write lands on the tracker.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WriteTarget {
    /// A label (additive/subtractive endpoint).
    Label(String),
    /// A named custom field.
    CustomField(String),
    /// A project field.
    ProjectField(String),
}

impl WriteTarget {
    fn describe(&self) -> String {
        match self {
            Self::Label(n) => format!("label {n}"),
            Self::CustomField(n) => format!("field {n}"),
            Self::ProjectField(n) => format!("project field {n}"),
        }
    }
}

/// One authorized write; only [`FieldOwnership::authorize`] can build it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WriteOp {
    target: WriteTarget,
    value: Option<String>,
}

impl WriteOp {
    /// Where the write lands.
    pub fn target(&self) -> &WriteTarget {
        &self.target
    }

    /// The value written (`None` for a label, whose name is its value).
    pub fn value(&self) -> Option<&str> {
        self.value.as_deref()
    }
}

/// Validated field ownership.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FieldOwnership {
    owners: BTreeMap<String, Owner>,
    tracker_owned: BTreeSet<String>,
}

impl FieldOwnership {
    /// Check `cfg` covers exactly the `projected` fields, each with one owner.
    ///
    /// # Errors
    /// [`FieldsError::Unowned`] naming the first projected field without an owner, or
    /// [`FieldsError::Unknown`] for an owner entry that is not a projected field.
    pub fn load(cfg: &FieldsConfig, projected: &[&str]) -> Result<Self, FieldsError> {
        if let Some(unknown) = cfg.owners.keys().find(|k| !projected.contains(&k.as_str())) {
            return Err(FieldsError::Unknown(unknown.clone()));
        }
        for field in projected {
            if !cfg.owners.contains_key(*field) {
                warn!(field, "projected field has no owner");
                return Err(FieldsError::Unowned((*field).to_owned()));
            }
        }
        debug!(
            owners = cfg.owners.len(),
            tracker_owned = cfg.tracker_owned.len(),
            "field ownership loaded"
        );
        Ok(Self {
            owners: cfg.owners.clone(),
            tracker_owned: cfg.tracker_owned.iter().cloned().collect(),
        })
    }

    /// The owner of projected field `field`, if it is projected.
    pub fn owner(&self, field: &str) -> Option<Owner> {
        self.owners.get(field).copied()
    }

    /// Turn `target` into a write, or refuse it when the tracker owns it.
    ///
    /// # Errors
    /// [`FieldsError::TrackerOwned`] for a label outside `frob:` or a listed field, and
    /// [`FieldsError::ProjectFieldReadOnly`] for a project field other than `status`.
    pub fn authorize(
        &self,
        target: WriteTarget,
        value: Option<String>,
    ) -> Result<WriteOp, FieldsError> {
        let refused = |target: &WriteTarget| FieldsError::TrackerOwned {
            target: target.describe(),
        };
        match &target {
            WriteTarget::Label(n) if !n.starts_with(MANAGED_LABEL_PREFIX) => {
                return Err(refused(&target));
            }
            WriteTarget::CustomField(n) if self.tracker_owned.contains(n) => {
                return Err(refused(&target));
            }
            WriteTarget::ProjectField(n) if n != PROJECT_STATUS_FIELD => {
                return Err(FieldsError::ProjectFieldReadOnly(n.clone()));
            }
            _ => {}
        }
        trace!(target = %target.describe(), "write authorized");
        Ok(WriteOp { target, value })
    }

    /// Turn planned mapping operations into writes, dropping (and logging) tracker-owned ones.
    pub fn plan_writes(&self, ops: &PlannedOps) -> Vec<WriteOp> {
        let labels = ops
            .labels
            .iter()
            .map(|l| (WriteTarget::Label(l.clone()), None));
        let fields = ops
            .fields
            .iter()
            .map(|(k, v)| (WriteTarget::CustomField(k.clone()), Some(v.clone())));
        labels
            .chain(fields)
            .filter_map(|(t, v)| match self.authorize(t, v) {
                Ok(op) => Some(op),
                Err(e) => {
                    debug!(error = %e, "write skipped");
                    None
                }
            })
            .collect()
    }

    /// Writes for project fields: `status` only, every other field is read-only.
    pub fn plan_project_writes(&self, requested: &BTreeMap<String, String>) -> Vec<WriteOp> {
        requested
            .iter()
            .filter_map(|(k, v)| {
                match self.authorize(WriteTarget::ProjectField(k.clone()), Some(v.clone())) {
                    Ok(op) => Some(op),
                    Err(e) => {
                        debug!(error = %e, "project write skipped");
                        None
                    }
                }
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cfg(owned: &[&str], tracker: &[&str]) -> FieldsConfig {
        FieldsConfig {
            owners: owned
                .iter()
                .map(|f| ((*f).to_owned(), Owner::Repository))
                .collect(),
            tracker_owned: tracker.iter().map(|s| (*s).to_owned()).collect(),
        }
    }

    fn ownership(tracker: &[&str]) -> FieldOwnership {
        FieldOwnership::load(&cfg(&["priority"], tracker), &["priority"]).unwrap()
    }

    // frob:tests load
    #[test]
    fn unowned_projected_field_is_an_error_naming_it() {
        let err =
            FieldOwnership::load(&cfg(&["priority"], &[]), &["priority", "points"]).unwrap_err();
        assert_eq!(err, FieldsError::Unowned("points".into()));
        assert!(err.to_string().contains("points"));
        let err =
            FieldOwnership::load(&cfg(&["priority", "bogus"], &[]), &["priority"]).unwrap_err();
        assert_eq!(err, FieldsError::Unknown("bogus".into()));
        assert_eq!(ownership(&[]).owner("priority"), Some(Owner::Repository));
    }

    // frob:tests plan_writes
    #[test]
    fn tracker_owned_field_and_foreign_label_are_never_written() {
        let o = ownership(&["Notes"]);
        let mut ops = PlannedOps {
            labels: vec!["frob:managed".into(), "bug".into()],
            ..Default::default()
        };
        ops.fields.insert("Notes".into(), "x".into());
        ops.fields.insert("Prio".into(), "high".into());
        let writes = o.plan_writes(&ops);
        let targets: Vec<_> = writes.iter().map(|w| w.target().clone()).collect();
        assert_eq!(
            targets,
            [
                WriteTarget::Label("frob:managed".into()),
                WriteTarget::CustomField("Prio".into())
            ]
        );
        assert_eq!(writes[1].value(), Some("high"));
    }

    // frob:tests authorize
    #[test]
    fn authorize_refuses_tracker_owned_targets() {
        let o = ownership(&["Notes"]);
        assert!(matches!(
            o.authorize(WriteTarget::Label("bug".into()), None),
            Err(FieldsError::TrackerOwned { .. })
        ));
        assert!(matches!(
            o.authorize(WriteTarget::CustomField("Notes".into()), Some("x".into())),
            Err(FieldsError::TrackerOwned { .. })
        ));
        assert!(
            o.authorize(WriteTarget::Label("frob:managed".into()), None)
                .is_ok()
        );
    }

    // frob:tests plan_project_writes
    #[test]
    fn only_project_status_is_writable() {
        let o = ownership(&[]);
        let req: BTreeMap<String, String> = [("status", "Done"), ("sprint", "3"), ("size", "L")]
            .iter()
            .map(|(k, v)| ((*k).to_owned(), (*v).to_owned()))
            .collect();
        let writes = o.plan_project_writes(&req);
        assert_eq!(writes.len(), 1);
        assert_eq!(
            writes[0].target(),
            &WriteTarget::ProjectField("status".into())
        );
        assert_eq!(
            o.authorize(WriteTarget::ProjectField("sprint".into()), None),
            Err(FieldsError::ProjectFieldReadOnly("sprint".into()))
        );
    }
}
