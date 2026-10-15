//! The pack drift-lock `grimble.packs.lock` (packs.md sections 2.5 and 4, security.md 2.1).
//!
//! The lock pins, per enabled pack, its name, version, TREE digest (every byte, the trust
//! input), declared effects and the SEMANTIC item digests (documentary text excluded, the
//! noise-free input of PACK001 drift reporting). Only an explicit update writes it; the file
//! name is a parameter because each product names its own lock.

// frob:ticket 01M3ZX7FTSKACE9TE7MBHQH7ET

mod io;
mod semantic;
mod verify;

pub use io::{read, write};
pub use semantic::{item_digest, snapshot};
pub use verify::{ItemChange, LockFinding, verify};

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

/// The lock file layout version this build reads and writes.
pub const LOCK_VERSION: u32 = 1;
/// The item and pack digest scheme this build computes.
pub const DIGEST_SCHEME: u32 = 1;

/// One pinned pack: what a lock records and what a live pack is compared as.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LockedPack {
    /// The pack name.
    pub name: String,
    /// The pack version.
    pub version: String,
    /// The `blake3:` tree digest over every byte of the pack.
    pub tree: String,
    /// Declared effects, by family.
    #[serde(default)]
    pub effects: BTreeMap<String, Vec<String>>,
    /// Semantic item key to `blake3:` item digest.
    #[serde(default)]
    pub items: BTreeMap<String, String>,
}

/// The whole lock file.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Lock {
    /// The lock layout version.
    pub lock_version: u32,
    /// The digest scheme of the item and tree digests.
    pub digest_scheme: u32,
    /// One entry per enabled pack, sorted by name.
    #[serde(default)]
    pub pack: Vec<LockedPack>,
}

impl Lock {
    /// Builds a current-scheme lock from `packs`, sorted by name.
    pub fn new(mut packs: Vec<LockedPack>) -> Self {
        packs.sort_by(|a, b| a.name.cmp(&b.name));
        Self {
            lock_version: LOCK_VERSION,
            digest_scheme: DIGEST_SCHEME,
            pack: packs,
        }
    }
}
