//! The per-ecosystem build-output adapter and the generic eviction plan over its units.
//!
//! An adapter knows an ecosystem's layout: where its output directories sit in a
//! checkout and which pieces of them can be removed and rebuilt. The plan is
//! ecosystem-independent: incremental state past its age goes first, then the
//! oldest artifacts until the directory fits its budget, never touching anything
//! within the keep window of the newest artifact (the latest build).
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

/// What a removable unit is, which decides the rule that applies to it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UnitKind {
    /// Incremental-compilation state: removed once unused past the age, budget aside.
    Incremental,
    /// A build artifact: evicted oldest first while over budget, unless recent.
    Artifact,
}

/// One removable piece of build output (an incremental directory, or the files of one compilation unit).
#[derive(Debug, Clone)]
pub struct Unit {
    /// Paths removed together.
    pub paths: Vec<PathBuf>,
    /// How the plan treats it.
    pub kind: UnitKind,
    /// Total bytes of the paths.
    pub bytes: u64,
    /// Latest modification time among them.
    pub modified: SystemTime,
    /// Short name for reports.
    pub label: String,
}

/// The knobs a plan needs, from `[gc]`.
#[derive(Debug, Clone)]
pub struct BuildPolicy {
    /// Incremental state unused for longer than this is removed.
    pub incremental_max_age: Duration,
    /// Artifacts within this window of the newest artifact are the latest build's and stay.
    pub keep_recent: Duration,
    /// Bytes the output directory may hold.
    pub budget_bytes: u64,
    /// Binary names whose output is never listed as a unit.
    pub keep_binaries: Vec<String>,
}

/// An ecosystem's build output: where it is and what can go.
pub trait BuildAdapter {
    /// Short name for reports (`cargo`).
    fn name(&self) -> &'static str;

    /// The existing output directories this adapter owns in `checkout`.
    fn output_dirs(&self, checkout: &Path) -> Vec<PathBuf>;

    /// The removable units inside one output directory; protected output is not listed.
    fn units(&self, dir: &Path, policy: &BuildPolicy) -> Vec<Unit>;
}

/// The units chosen for removal from one output directory, and why none more.
#[derive(Debug, Clone, Default)]
pub struct Plan {
    /// Units to remove, incremental first, then oldest artifacts.
    pub evict: Vec<Unit>,
    /// Bytes the output directory holds after `evict` (an estimate from `total_bytes`).
    pub remaining_bytes: u64,
    /// True when the directory is still over budget because only recent artifacts are left.
    pub over_budget_kept_recent: bool,
}

/// Decide what to evict from a directory of `total_bytes` holding `units`, at time `now`.
pub fn plan(units: Vec<Unit>, total_bytes: u64, now: SystemTime, policy: &BuildPolicy) -> Plan {
    let mark = units
        .iter()
        .filter(|u| u.kind == UnitKind::Artifact)
        .map(|u| u.modified)
        .max();
    let protect_from = mark.map(|m| {
        m.checked_sub(policy.keep_recent)
            .unwrap_or(SystemTime::UNIX_EPOCH)
    });
    let mut evict = Vec::new();
    let mut remaining = total_bytes;
    let mut artifacts = Vec::new();
    for u in units {
        match u.kind {
            UnitKind::Incremental => {
                let age = now.duration_since(u.modified).unwrap_or_default();
                if age > policy.incremental_max_age {
                    remaining = remaining.saturating_sub(u.bytes);
                    evict.push(u);
                }
            }
            UnitKind::Artifact => artifacts.push(u),
        }
    }
    artifacts.sort_by_key(|u| u.modified);
    let mut over = false;
    for u in artifacts {
        if remaining <= policy.budget_bytes {
            break;
        }
        if protect_from.is_some_and(|p| u.modified >= p) {
            over = true;
            break;
        }
        remaining = remaining.saturating_sub(u.bytes);
        evict.push(u);
    }
    Plan {
        evict,
        remaining_bytes: remaining,
        over_budget_kept_recent: over && remaining > policy.budget_bytes,
    }
}
