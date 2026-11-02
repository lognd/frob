//! The PACK pass of `grimble check`: PACK005 and PACK006 over the enabled repository packs.
//!
//! The pass hands what [`crate::packs::load`] found to `grimble_capabilities::pack_rules::evaluate`.
//! A repository pack file (`local/NAME`, tier 1) has no manifest, so there is nothing to snapshot
//! and the lock cannot be compared: PACK001 stays unevaluated (and so does PACK002 to PACK004,
//! PACK007 and PACK008, which need the full loader). An unreadable file is PACK006 (Unresolved), a
//! file that does not parse is PACK005, and an enabled id this build cannot load at all is PACK006.

// frob:ticket 01M5A56QBF8SQBSZ5QSSZ6F835

use std::collections::BTreeMap;

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

/// The rules this pass evaluates; the others need the full pack loader and the lock.
pub const EVALUATED: [&str; 2] = ["PACK005", "PACK006"];

/// Run the PACK pass over the packs `loaded` describes (`enabled` counts the ids that were asked for).
pub fn analyze(loaded: &LoadedPacks, enabled: usize) -> PackReport {
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
    let findings = evaluate(None, &states, &issues);
    let subjects = if enabled == 0 {
        BTreeMap::new()
    } else {
        EVALUATED.iter().map(|id| (*id, enabled)).collect()
    };
    tracing::debug!(
        enabled,
        findings = findings.len(),
        "pack pass over repository packs"
    );
    PackReport { findings, subjects }
}
