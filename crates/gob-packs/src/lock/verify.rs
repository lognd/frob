//! Comparing a lock with the live enabled packs (PACK001).

use std::collections::BTreeMap;

use tracing::debug;

use super::{DIGEST_SCHEME, LOCK_VERSION, Lock, LockedPack};

/// How one item differs from the lock.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ItemChange {
    /// In the live pack, not in the lock.
    Added,
    /// In the lock, not in the live pack.
    Removed,
    /// In both with different digests.
    Changed,
}

/// One PACK001 outcome of [`verify`]; an empty list means the lock holds.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LockFinding {
    /// PACK001 `lock-missing`: an enabled pack is not locked.
    LockMissing {
        /// The enabled pack.
        name: String,
    },
    /// PACK001 `lock-stale`: a locked pack is no longer enabled.
    LockStale {
        /// The locked pack.
        name: String,
    },
    /// PACK001 `scheme`: the lock was written by another layout or digest scheme.
    Scheme {
        /// Why it cannot be compared.
        reason: String,
    },
    /// PACK001 pack-level: the version differs.
    Version {
        /// The pack.
        name: String,
        /// Locked version.
        locked: String,
        /// Live version.
        current: String,
    },
    /// PACK001 pack-level: declared effects differ.
    Effects {
        /// The pack.
        name: String,
    },
    /// PACK001 per item.
    Item {
        /// The pack.
        name: String,
        /// The item key.
        key: String,
        /// How it differs.
        change: ItemChange,
        /// True when the version is unchanged (content changed without a bump).
        without_version_bump: bool,
    },
    /// Only the tree digest differs: semantic digests match (a documentation-only edit).
    /// Not a re-lock, but trust must be re-granted.
    TreeOnly {
        /// The pack.
        name: String,
        /// Locked tree digest.
        locked: String,
        /// Live tree digest.
        current: String,
    },
}

impl LockFinding {
    /// The stable rule id: every lock finding is PACK001.
    pub fn code(&self) -> &'static str {
        "PACK001"
    }
}

fn item_changes(l: &LockedPack, c: &LockedPack, bump: bool, out: &mut Vec<LockFinding>) {
    let mut push = |key: &str, change| {
        out.push(LockFinding::Item {
            name: c.name.clone(),
            key: key.to_owned(),
            change,
            without_version_bump: !bump,
        });
    };
    for (k, d) in &c.items {
        match l.items.get(k) {
            None => push(k, ItemChange::Added),
            Some(o) if o != d => push(k, ItemChange::Changed),
            Some(_) => {}
        }
    }
    for k in l.items.keys().filter(|k| !c.items.contains_key(*k)) {
        push(k, ItemChange::Removed);
    }
}

/// Compares `lock` with the live enabled `current` packs.
///
/// A scheme mismatch returns a single `Scheme` finding. Otherwise findings are ordered by
/// pack name: missing and stale packs, then version, effects and item changes; when only the
/// tree digest differs a single `TreeOnly` is reported.
pub fn verify(lock: &Lock, current: &[LockedPack]) -> Vec<LockFinding> {
    if lock.lock_version != LOCK_VERSION || lock.digest_scheme != DIGEST_SCHEME {
        return vec![LockFinding::Scheme {
            reason: format!(
                "lock_version {} / digest_scheme {} differ from this binary's {LOCK_VERSION} / {DIGEST_SCHEME}",
                lock.lock_version, lock.digest_scheme
            ),
        }];
    }
    let locked: BTreeMap<&str, &LockedPack> =
        lock.pack.iter().map(|p| (p.name.as_str(), p)).collect();
    let live: BTreeMap<&str, &LockedPack> = current.iter().map(|p| (p.name.as_str(), p)).collect();
    let mut out = Vec::new();
    for (name, c) in &live {
        let Some(l) = locked.get(name) else {
            out.push(LockFinding::LockMissing {
                name: (*name).to_owned(),
            });
            continue;
        };
        let before = out.len();
        let bump = l.version != c.version;
        if bump {
            out.push(LockFinding::Version {
                name: (*name).to_owned(),
                locked: l.version.clone(),
                current: c.version.clone(),
            });
        }
        if l.effects != c.effects {
            out.push(LockFinding::Effects {
                name: (*name).to_owned(),
            });
        }
        item_changes(l, c, bump, &mut out);
        if out.len() == before && l.tree != c.tree {
            out.push(LockFinding::TreeOnly {
                name: (*name).to_owned(),
                locked: l.tree.clone(),
                current: c.tree.clone(),
            });
        }
    }
    for name in locked.keys().filter(|n| !live.contains_key(*n)) {
        out.push(LockFinding::LockStale {
            name: (*name).to_owned(),
        });
    }
    debug!(findings = out.len(), "pack lock verified");
    out
}
