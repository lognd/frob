//! Repository-level inventory of managed labels, milestones and issue types (mirror.md 3.4, 3.6).
//!
//! The inventory stores id to name for each kind. Comparing the stored copy with a fresh read
//! records a repository-level rename or removal once, with a fidelity gap, instead of once per
//! issue; the fresh read then becomes the stored copy, so the same change is never recorded twice.

// frob:ticket 01M4052R4AEFJ2MQ2H9A9X0DN3

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use tracing::{debug, info};

use crate::github::read::Fidelity;

/// Which repository-level object a name belongs to.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    /// A label.
    Label,
    /// A milestone.
    Milestone,
    /// An issue type.
    IssueType,
}

/// Stored names by tracker id, per kind.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Inventory {
    /// Label id to name.
    pub labels: BTreeMap<u64, String>,
    /// Milestone id to title.
    pub milestones: BTreeMap<u64, String>,
    /// Issue type id to name.
    pub issue_types: BTreeMap<u64, String>,
}

/// What happened to one repository-level object since the stored inventory.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ChangeKind {
    /// The object is new.
    Added {
        /// Its name.
        name: String,
    },
    /// The id now has a different name.
    Renamed {
        /// The stored name.
        from: String,
        /// The current name.
        to: String,
    },
    /// The id is gone.
    Removed {
        /// The stored name.
        name: String,
    },
}

/// One recorded repository-level change with its fidelity.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RecordedChange {
    /// The kind of object.
    pub kind: Kind,
    /// The tracker id.
    pub id: u64,
    /// What changed.
    pub change: ChangeKind,
    /// `Gap` for renames and removals (issue history cannot say who or why), else `Full`.
    pub fidelity: Fidelity,
}

fn diff_kind(
    kind: Kind,
    old: &BTreeMap<u64, String>,
    new: &BTreeMap<u64, String>,
    out: &mut Vec<RecordedChange>,
) {
    for (id, name) in new {
        let (change, fidelity) = match old.get(id) {
            None => (ChangeKind::Added { name: name.clone() }, Fidelity::Full),
            Some(was) if was != name => (
                ChangeKind::Renamed {
                    from: was.clone(),
                    to: name.clone(),
                },
                Fidelity::Gap,
            ),
            Some(_) => continue,
        };
        out.push(RecordedChange {
            kind,
            id: *id,
            change,
            fidelity,
        });
    }
    for (id, name) in old.iter().filter(|(id, _)| !new.contains_key(id)) {
        out.push(RecordedChange {
            kind,
            id: *id,
            change: ChangeKind::Removed { name: name.clone() },
            fidelity: Fidelity::Gap,
        });
    }
}

/// Compare the stored inventory with a fresh read; returns the new stored copy and the changes.
///
/// The returned inventory equals `current`, so reconciling again against it yields no changes:
/// a rename is recorded once, not per issue and not per run.
pub fn reconcile(stored: &Inventory, current: &Inventory) -> (Inventory, Vec<RecordedChange>) {
    let mut changes = Vec::new();
    diff_kind(Kind::Label, &stored.labels, &current.labels, &mut changes);
    diff_kind(
        Kind::Milestone,
        &stored.milestones,
        &current.milestones,
        &mut changes,
    );
    diff_kind(
        Kind::IssueType,
        &stored.issue_types,
        &current.issue_types,
        &mut changes,
    );
    for c in &changes {
        if c.fidelity == Fidelity::Gap {
            info!(kind = ?c.kind, id = c.id, change = ?c.change, "inventory: repository-level change, fidelity gap");
        } else {
            debug!(kind = ?c.kind, id = c.id, change = ?c.change, "inventory: repository-level change");
        }
    }
    (current.clone(), changes)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn inv(label: &str) -> Inventory {
        Inventory {
            labels: BTreeMap::from([(1, label.to_owned())]),
            ..Inventory::default()
        }
    }

    // frob:tests reconcile
    #[test]
    fn label_rename_is_recorded_once_with_gap() {
        let stored = inv("frob:managed");
        let current = inv("frob:mirrored");
        let (next, changes) = reconcile(&stored, &current);
        assert_eq!(changes.len(), 1);
        assert_eq!(changes[0].kind, Kind::Label);
        assert_eq!(changes[0].fidelity, Fidelity::Gap);
        assert_eq!(
            changes[0].change,
            ChangeKind::Renamed {
                from: "frob:managed".into(),
                to: "frob:mirrored".into()
            }
        );
        let (_, again) = reconcile(&next, &current);
        assert!(again.is_empty());
    }

    // frob:tests reconcile
    #[test]
    fn removal_is_a_gap_and_addition_is_full() {
        let (_, removed) = reconcile(&inv("a"), &Inventory::default());
        assert_eq!(removed[0].fidelity, Fidelity::Gap);
        let (_, added) = reconcile(&Inventory::default(), &inv("a"));
        assert_eq!(added[0].fidelity, Fidelity::Full);
    }
}
