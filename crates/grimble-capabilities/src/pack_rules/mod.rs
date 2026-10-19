//! PACK001 to PACK008 findings (packs.md section 9, security.md section 4).
//!
//! [`evaluate`] is the one pass: it compares the live enabled packs with the lock (PACK001),
//! turns packs that could not be loaded into PACK006 (a required Unresolved when the pack is
//! required) and skips PACK001 for those packs, then maps per-pack [`PackIssue`]s to PACK002 to
//! PACK008. PACK009 is retired and never reused.

// frob:ticket 01M3ZX7K3N8AWVBTZ90E0F1YSP

mod host;
/// Rule `PACK001`.
pub mod pack001;
/// Rule `PACK002`.
pub mod pack002;
/// Rule `PACK003`.
pub mod pack003;
/// Rule `PACK004`.
pub mod pack004;
/// Rule `PACK005`.
pub mod pack005;
/// Rule `PACK006`.
pub mod pack006;
/// Rule `PACK007`.
pub mod pack007;
/// Rule `PACK008`.
pub mod pack008;

use std::collections::BTreeSet;

use gob_packs::lock::{ItemChange, Lock, LockFinding, LockedPack, verify};
use gob_rules::{Finding, PackFailure, RequiredReason, RuleId, Severity, UnresolvedReason};
use tracing::{debug, info, warn};

pub use host::PackHost;
pub use pack001::Pack001;
pub use pack002::Pack002;
pub use pack003::Pack003;
pub use pack004::Pack004;
pub use pack005::Pack005;
pub use pack006::Pack006;
pub use pack007::Pack007;
pub use pack008::Pack008;

/// The reason code PACK006 carries on its Unresolved finding.
pub const UNAVAILABLE_REASON: &str = "pack-unavailable";

/// An enabled pack as the pack pass found it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PackState {
    /// The pack loaded; compared with the lock.
    Loaded(LockedPack),
    /// The pack could not be loaded; PACK006, and PACK001 does not evaluate it.
    Unavailable {
        /// The pack name.
        name: String,
        /// True when the pack is marked required, so the Unresolved fails the gate.
        required: bool,
    },
}

/// A per-pack problem found while reading a pack, one per PACK002 to PACK005, PACK007, PACK008.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PackIssue {
    /// PACK002: a capability atom the registry does not know.
    UnknownAtom {
        /// The pack.
        pack: String,
        /// The atom.
        atom: String,
    },
    /// PACK003: a detector that is unavailable.
    DetectorUnavailable {
        /// The pack.
        pack: String,
        /// The detector.
        detector: String,
    },
    /// PACK004: an item declared twice.
    Duplicate {
        /// The pack.
        pack: String,
        /// The item key.
        key: String,
    },
    /// PACK005: a malformed pack file.
    Malformed {
        /// The pack.
        pack: String,
        /// What is wrong.
        detail: String,
    },
    /// PACK007: an infer rule that does not exist.
    UnknownInferRule {
        /// The pack.
        pack: String,
        /// The rule name.
        rule: String,
    },
    /// PACK008: an override that restates the pack.
    RedundantOverride {
        /// The pack.
        pack: String,
        /// The overridden key.
        key: String,
    },
}

/// The rule id `code`; the codes here are literals, so a parse failure is a programmer bug.
fn rid(code: &str) -> RuleId {
    code.parse().expect("PACK rule ids are well formed")
}

/// The PACK001 reason word of a lock finding: changed, added, removed, lock-missing, or the pack-level kind.
pub fn lock_reason(f: &LockFinding) -> &'static str {
    match f {
        LockFinding::LockMissing { .. } => "lock-missing",
        LockFinding::LockStale { .. } => "lock-stale",
        LockFinding::Scheme { .. } => "scheme",
        LockFinding::Version { .. } => "version",
        LockFinding::Effects { .. } => "effects",
        LockFinding::Item { change, .. } => match change {
            ItemChange::Added => "added",
            ItemChange::Removed => "removed",
            ItemChange::Changed => "changed",
        },
        LockFinding::TreeOnly { .. } => "tree-only",
    }
}

/// One PACK001 finding for a lock finding, anchored on the pack (and item) it concerns.
fn lock_finding(f: &LockFinding) -> Finding {
    let reason = lock_reason(f);
    let (anchor, message) = match f {
        LockFinding::LockMissing { name } => (
            name.clone(),
            format!("pack `{name}` is not locked ({reason})"),
        ),
        LockFinding::LockStale { name } => (
            name.clone(),
            format!("lock entry `{name}` is no longer enabled ({reason})"),
        ),
        LockFinding::Scheme { reason: why } => (
            "lock".to_owned(),
            format!("the lock cannot be compared ({reason}): {why}"),
        ),
        LockFinding::Version {
            name,
            locked,
            current,
        } => (
            name.clone(),
            format!("pack `{name}` version {locked} is locked, {current} is live ({reason})"),
        ),
        LockFinding::Effects { name } => (
            name.clone(),
            format!("pack `{name}` declared effects differ from the lock ({reason})"),
        ),
        LockFinding::Item {
            name,
            key,
            without_version_bump,
            ..
        } => {
            let bump = if *without_version_bump {
                " without a version bump"
            } else {
                ""
            };
            (
                format!("{name}::{key}"),
                format!("pack `{name}` item `{key}` {reason}{bump}"),
            )
        }
        LockFinding::TreeOnly { name, .. } => (
            name.clone(),
            format!("pack `{name}` differs from the lock only in its tree digest ({reason})"),
        ),
    };
    Finding::new(rid(f.code()), Severity::Error, None, message, &anchor)
}

/// PACK006 for an unavailable pack: Unresolved, required when the pack is.
fn unavailable_finding(name: &str, required: bool) -> Finding {
    let mut f = Finding::new(
        rid("PACK006"),
        Severity::Unresolved,
        None,
        format!("enabled pack `{name}` could not be loaded"),
        name,
    )
    .with_reason(UnresolvedReason::from_code(UNAVAILABLE_REASON));
    if let Some(r) = RequiredReason::for_pack(required, name, PackFailure::PackUnavailable) {
        f = f.with_required(r);
    }
    f
}

/// The finding for a per-pack issue (PACK002 to PACK005, PACK007, PACK008).
pub fn issue_finding(issue: &PackIssue) -> Finding {
    let (code, sev, anchor, msg) = match issue {
        PackIssue::UnknownAtom { pack, atom } => (
            "PACK002",
            Severity::Error,
            format!("{pack}::{atom}"),
            format!("pack `{pack}` names unknown atom `{atom}`"),
        ),
        PackIssue::DetectorUnavailable { pack, detector } => (
            "PACK003",
            Severity::Warn,
            format!("{pack}::{detector}"),
            format!("pack `{pack}` detector `{detector}` is unavailable"),
        ),
        PackIssue::Duplicate { pack, key } => (
            "PACK004",
            Severity::Error,
            format!("{pack}::{key}"),
            format!("pack `{pack}` declares `{key}` more than once"),
        ),
        PackIssue::Malformed { pack, detail } => (
            "PACK005",
            Severity::Error,
            pack.clone(),
            format!("pack `{pack}` is malformed: {detail}"),
        ),
        PackIssue::UnknownInferRule { pack, rule } => (
            "PACK007",
            Severity::Error,
            format!("{pack}::{rule}"),
            format!("pack `{pack}` names unknown infer rule `{rule}`"),
        ),
        PackIssue::RedundantOverride { pack, key } => (
            "PACK008",
            Severity::Advisory,
            format!("{pack}::{key}"),
            format!("override of `{key}` in pack `{pack}` restates the pack"),
        ),
    };
    Finding::new(rid(code), sev, None, msg, &anchor)
}

/// Run the pack pass: PACK001 over loaded packs, PACK006 for unavailable ones, then `issues`.
///
/// An unavailable pack is neither compared with the lock nor reported stale, so PACK001 does not
/// evaluate it. A missing `lock` compares as an empty lock, so every loaded pack is lock-missing.
pub fn evaluate(lock: Option<&Lock>, packs: &[PackState], issues: &[PackIssue]) -> Vec<Finding> {
    let mut out = Vec::new();
    let mut failed = BTreeSet::new();
    let mut live = Vec::new();
    for p in packs {
        match p {
            PackState::Loaded(l) => live.push(l.clone()),
            PackState::Unavailable { name, required } => {
                warn!(pack = %name, required, "enabled pack unavailable");
                failed.insert(name.as_str());
                out.push(unavailable_finding(name, *required));
            }
        }
    }
    let base = match lock {
        Some(l) => Lock {
            pack: l
                .pack
                .iter()
                .filter(|p| !failed.contains(p.name.as_str()))
                .cloned()
                .collect(),
            ..l.clone()
        },
        None => Lock::new(Vec::new()),
    };
    let lock_findings = verify(&base, &live);
    debug!(
        count = lock_findings.len(),
        skipped = failed.len(),
        "PACK001 evaluated"
    );
    out.extend(lock_findings.iter().map(lock_finding));
    out.extend(issues.iter().map(issue_finding));
    info!(findings = out.len(), "pack pass done");
    out
}
