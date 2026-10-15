//! The plan cache for disk packs (plugins.md 6.1, security.md 2.2).
//!
//! A disk pack's GRL is compiled to plans on first load. The compiled plans
//! are stored outside the work tree, under the per-user XDG cache directory,
//! keyed by the pack tree digest and the engine fingerprint, and
//! authenticated with the machine MAC by [`gob_trust::StateStore`]. An entry
//! that fails its MAC, or whose bytes do not decode to valid plans, is
//! discarded and the pack is recompiled. The cache is best effort: an
//! unusable store only costs a recompile.

// frob:ticket 01M3ZX7JE252WBVE5DKMJK3JME

use std::path::Path;

use gob_plan::plan::Plan;
use gob_trust::{Lookup, MachineKey, StateError, StateStore};

use crate::{Digest, to_hex};

/// The state-store kind under which compiled packs are filed.
const KIND: &str = "plans";
/// The product directory name under the XDG cache root.
const PRODUCT: &str = "grimble";
/// Upper bound on plans in one entry; a larger count is treated as corrupt.
const MAX_PLANS: usize = 1 << 16;

/// Whether a load was served from the cache or compiled.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Source {
    /// Read from a verified cache entry; nothing was compiled.
    Cache,
    /// Compiled now (miss, or a discarded entry).
    Compiled,
}

/// The compiled plans of a pack and where they came from.
#[derive(Debug)]
pub struct Loaded {
    /// The plans in source order.
    pub plans: Vec<Plan>,
    /// Whether they came from the cache.
    pub source: Source,
}

/// A MAC'd cache of compiled pack plans outside the work tree.
#[derive(Debug)]
pub struct PlanCache {
    store: StateStore,
}

fn cache_id(tree: &Digest, engine: &str) -> String {
    format!("{}:{engine}", to_hex(tree))
}

fn encode(plans: &[Plan]) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(&(plans.len() as u64).to_le_bytes());
    for p in plans {
        let b = p.to_bytes();
        out.extend_from_slice(&(b.len() as u64).to_le_bytes());
        out.extend_from_slice(&b);
    }
    out
}

fn take_u64(bytes: &mut &[u8]) -> Option<usize> {
    let (head, rest) = bytes.split_first_chunk::<8>()?;
    *bytes = rest;
    usize::try_from(u64::from_le_bytes(*head)).ok()
}

/// Decodes an entry payload; `None` when it is malformed or holds an invalid plan.
fn decode(mut bytes: &[u8]) -> Option<Vec<Plan>> {
    let n = take_u64(&mut bytes)?;
    if n > MAX_PLANS {
        return None;
    }
    let mut plans = Vec::new();
    for _ in 0..n {
        let len = take_u64(&mut bytes)?;
        if len > bytes.len() {
            return None;
        }
        let (body, rest) = bytes.split_at(len);
        bytes = rest;
        plans.push(Plan::load(body).ok()?);
    }
    bytes.is_empty().then_some(plans)
}

impl PlanCache {
    /// Opens the per-user cache under `$XDG_CACHE_HOME/grimble/`, refusing a root inside `work_tree`.
    ///
    /// # Errors
    /// [`StateError`] when the key or directory cannot be obtained; callers then compile without a cache.
    pub fn open_default(work_tree: Option<&Path>) -> Result<Self, StateError> {
        Ok(Self {
            store: StateStore::open_default(PRODUCT, work_tree)?,
        })
    }

    /// Opens a cache rooted at `root` with `key` (tests and embedders), refusing a root inside `work_tree`.
    ///
    /// # Errors
    /// [`StateError`] when the root is inside the work tree or cannot be created.
    pub fn open_at(
        root: std::path::PathBuf,
        key: MachineKey,
        work_tree: Option<&Path>,
    ) -> Result<Self, StateError> {
        Ok(Self {
            store: StateStore::open_at(root, key, work_tree)?,
        })
    }

    /// Returns the cached plans for (`tree`, `engine`), or runs `compile` and caches its result.
    ///
    /// A corrupt, tampered or undecodable entry is discarded and rebuilt; a failing
    /// store is logged and skipped, so only `compile`'s own error can fail the call.
    ///
    /// # Errors
    /// Whatever `compile` returns when the plans must be built and cannot be.
    pub fn load_or_compile<E>(
        &self,
        tree: &Digest,
        engine: &str,
        compile: impl FnOnce() -> Result<Vec<Plan>, E>,
    ) -> Result<Loaded, E> {
        let id = cache_id(tree, engine);
        match self.store.get(KIND, &id) {
            Ok(Lookup::Hit(payload)) => {
                if let Some(plans) = decode(&payload) {
                    tracing::debug!(id = %id, plans = plans.len(), "plan cache hit");
                    return Ok(Loaded {
                        plans,
                        source: Source::Cache,
                    });
                }
                tracing::warn!(id = %id, "plan cache entry does not decode; rebuilding");
            }
            Ok(Lookup::Miss) => tracing::debug!(id = %id, "plan cache miss"),
            Ok(Lookup::Discarded(why)) => {
                tracing::warn!(id = %id, ?why, "plan cache entry discarded; rebuilding");
            }
            Err(e) => tracing::warn!(error = %e, "plan cache unreadable; compiling"),
        }
        let plans = compile()?;
        if let Err(e) = self.store.put(KIND, &id, &encode(&plans)) {
            tracing::warn!(error = %e, "plan cache write failed; continuing uncached");
        }
        Ok(Loaded {
            plans,
            source: Source::Compiled,
        })
    }
}
