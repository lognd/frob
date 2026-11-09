//! The PACK pass of `grimble check`: PACK005 and PACK006 over the enabled repository packs.
//!
//! The pass hands what [`crate::packs::load`] found to `grimble_capabilities::pack_rules::evaluate`.
//! A repository pack file (`local/NAME`, tier 1) has no manifest, so there is nothing to snapshot
//! and the lock cannot be compared. The one exception is the built-in `core-effects` pack, which is
//! embedded in the binary: when `grimble.packs.lock` exists its core-effects entry is compared with
//! the embedded pack (PACK001 lock drift). PACK002 to PACK004, PACK007 and PACK008 stay
//! unevaluated, as they need the full loader. An unreadable file is PACK006 (Unresolved), a
//! file that does not parse is PACK005, and an enabled id this build cannot load at all is PACK006.

// frob:ticket 01M5A56QBF8SQBSZ5QSSZ6F835
// frob:ticket 01M665STQ6VPTEB61Z68K6G441

use std::collections::BTreeMap;
use std::path::Path;

use gob_packs::core_effects;
use gob_packs::lock::{self, Lock};
use gob_rules::Finding;
use grimble_capabilities::pack_rules::{PackIssue, PackState, evaluate};

use crate::packs::LoadedPacks;

/// What the PACK pass found: its findings and the subjects it examined per rule.
#[derive(Debug, Clone, Default)]
pub struct PackReport {
    /// The PACK findings, anchored on pack ids.
    pub findings: Vec<Finding>,
    /// Subjects (enabled packs) examined, by rule id; only rules the pass evaluates appear.
    pub subjects: BTreeMap<&'static str, usize>,
}

/// The rules this pass evaluates for every enabled pack; the others need the full pack loader.
pub const EVALUATED: [&str; 2] = ["PACK005", "PACK006"];

/// The lock file name, at the repository root.
pub const LOCK_FILE: &str = "grimble.packs.lock";

/// The lock restricted to the embedded core-effects entry, or `None` when there is no lock to read.
///
/// Other entries are dropped: this pass loads only core-effects, so they would read as stale.
fn core_lock(root: &Path) -> Option<Lock> {
    let path = root.join(LOCK_FILE);
    if !path.is_file() {
        tracing::debug!(path = %path.display(), "no pack lock; core-effects drift not checked");
        return None;
    }
    match lock::read(&path) {
        Ok(mut l) => {
            l.pack.retain(|p| p.name == gob_ir::core_pack::OWNER);
            Some(l)
        }
        Err(e) => {
            tracing::warn!(error = %e, "pack lock unreadable; core-effects drift not checked");
            None
        }
    }
}

/// PACK001 findings for core-effects lock drift, or `None` when it was not evaluated.
fn core_drift(root: &Path) -> Option<Vec<Finding>> {
    let lock = core_lock(root)?;
    match core_effects::locked() {
        Ok(live) => Some(evaluate(Some(&lock), &[PackState::Loaded(live)], &[])),
        Err(e) => {
            tracing::warn!(error = %e, "embedded core-effects pack unreadable; drift not checked");
            None
        }
    }
}

/// Run the PACK pass over the packs `loaded` describes (`enabled` counts the ids that were asked for).
///
/// `root` is the repository root, where `grimble.packs.lock` is looked up for core-effects drift.
pub fn analyze(root: &Path, loaded: &LoadedPacks, enabled: usize) -> PackReport {
    let states: Vec<PackState> = loaded
        .unavailable
        .iter()
        .chain(&loaded.unsupported)
        .map(|name| PackState::Unavailable {
            name: name.clone(),
            required: false,
        })
        .collect();
    let issues: Vec<PackIssue> = loaded.issues.clone();
    let mut findings = evaluate(None, &states, &issues);
    // evaluate(None, ..) with no loaded pack yields no PACK001, so drift is a separate evaluation.
    let drift = core_drift(root);
    let mut subjects: BTreeMap<&'static str, usize> = if enabled == 0 {
        BTreeMap::new()
    } else {
        EVALUATED.iter().map(|id| (*id, enabled)).collect()
    };
    if let Some(d) = drift {
        findings.extend(d);
        subjects.insert("PACK001", 1);
    }
    tracing::debug!(
        enabled,
        findings = findings.len(),
        "pack pass over repository packs"
    );
    PackReport { findings, subjects }
}
