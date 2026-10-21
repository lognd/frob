//! The repository pack loader for tiers 1 and 2 (plugins.md section 2, security.md 2.1 and 2.2).
//!
//! [`load_pack`] loads one `packs/<name>/` directory: it reads the manifest and each content
//! file once into memory, interns tier-1 atoms into the registry, compiles tier-2 GRL rules
//! (through the plan cache when one is given), computes the tree digest and verifies the pack
//! against the lock. Tier 3 (WASM) is refused until the trust store and sandbox land: the pack's
//! wasm components are reported as [`Unavailable`] (PACK006, Unresolved `pack-unavailable`) with
//! the reason, never dropped silently. Nothing is registered unless every fallible step succeeds.

// frob:ticket 01M3ZX7K7BN0CEADJFMCTGEA64

mod read;

use std::path::Path;

use gob_plan::lower::lower_source;
use gob_plan::plan::Plan;

use crate::error::PackError;
use crate::lock::{Lock, LockFinding, LockedPack, snapshot, verify};
use crate::tier1::{self, Content, Tier1Error};
use crate::{Digest, Manifest, PlanCache, Provenance, Source, tree_digest};

/// The Unresolved reason code reported for a pack that cannot be loaded.
pub const REASON_PACK_UNAVAILABLE: &str = "pack-unavailable";
/// The rule id of an unloadable pack (packs.md section 9).
pub const UNAVAILABLE_CODE: &str = "PACK006";
/// Why tier-3 content is refused today.
pub const TIER3_REASON: &str =
    "tier-3 wasm packs need the trust store and sandbox, which are not enabled yet";

/// Why a repository pack failed to load.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum LoadError {
    /// PACK005 or PACK004 from the manifest, a content file or a rule file.
    #[error(transparent)]
    Pack(#[from] PackError),
    /// PACK005 or PACK004 from tier-1 content.
    #[error(transparent)]
    Tier1(#[from] Tier1Error),
}

impl LoadError {
    /// The stable rule id of this error.
    pub fn code(&self) -> crate::PackCode {
        match self {
            Self::Pack(e) => e.code(),
            Self::Tier1(e) => e.code(),
        }
    }
}

/// Pack content that is present but cannot run: PACK006 Unresolved `pack-unavailable`, required.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Unavailable {
    /// The pack name.
    pub pack: String,
    /// The provenance label, for example `repo:packs/py-safety`.
    pub provenance: String,
    /// The pack's declared rule families the unavailable content would have served.
    pub families: Vec<String>,
    /// The tier-3 component files that were not loaded.
    pub components: Vec<String>,
    /// Why they were not loaded.
    pub reason: String,
}

impl Unavailable {
    /// The stable rule id, always PACK006.
    pub fn code(&self) -> &'static str {
        UNAVAILABLE_CODE
    }

    /// The Unresolved reason code, always `pack-unavailable`.
    pub fn reason_code(&self) -> &'static str {
        REASON_PACK_UNAVAILABLE
    }
}

/// Inputs to [`load_pack`] besides the directory.
#[derive(Debug, Default, Clone, Copy)]
pub struct LoadOptions<'a> {
    /// The drift lock to verify against; `None` skips verification.
    pub lock: Option<&'a Lock>,
    /// The plan cache and engine fingerprint; `None` always compiles.
    pub cache: Option<(&'a PlanCache, &'a str)>,
}

/// A loaded repository pack.
#[derive(Debug)]
pub struct LoadedPack {
    /// The validated manifest.
    pub manifest: Manifest,
    /// The provenance label, `repo:packs/NAME`.
    pub provenance: String,
    /// The tier-1 content that was interned (empty when the pack declares none).
    pub content: Option<Content>,
    /// The compiled tier-2 plans in file then source order.
    pub plans: Vec<Plan>,
    /// Whether the plans came from the cache.
    pub source: Source,
    /// The tree digest over every byte of the pack.
    pub tree: Digest,
    /// The pack's current lock entry.
    pub locked: LockedPack,
    /// PACK001 findings against the given lock; empty when it holds or none was given.
    pub findings: Vec<LockFinding>,
    /// True when a lock was given and the pack matches it exactly.
    pub lock_verified: bool,
    /// Tier-3 content refused as PACK006 `pack-unavailable`; empty when the pack has none.
    pub unavailable: Vec<Unavailable>,
}

fn compile_rules(root: &Path, files: &[String]) -> Result<Vec<Plan>, PackError> {
    let mut plans = Vec::new();
    for rel in files {
        let (label, text) = read::read_text(root, rel, "provides.rules")?;
        let mut p = lower_source(rel, &text).map_err(|e| {
            PackError::malformed(&label, "provides.rules", format!("does not compile: {e}"))
        })?;
        plans.append(&mut p);
    }
    Ok(plans)
}

/// Loads the pack at `dir` (`packs/<name>`), registering its tier-1 atoms; see the module docs.
///
/// # Errors
/// [`LoadError`] as for [`inspect_pack`]; PACK004 when an atom is already declared.
/// On error nothing is registered.
pub fn load_pack(dir: &Path, opts: &LoadOptions<'_>) -> Result<LoadedPack, LoadError> {
    let loaded = inspect_pack(dir, opts)?;
    if let Some(c) = &loaded.content {
        tier1::intern(c)?;
    }
    tracing::info!(pack = %loaded.manifest.pack.name, provenance = %loaded.provenance, plans = loaded.plans.len(), lock_verified = loaded.lock_verified, "repository pack loaded");
    Ok(loaded)
}

/// Does everything [`load_pack`] does except register atoms: reads, parses, compiles, digests, verifies.
///
/// Used to build a lock entry for a pack before it is enabled.
///
/// # Errors
/// [`LoadError`]: PACK005 for an unreadable, oversized, malformed or misnamed pack file or a
/// directory whose name differs from `pack.name`.
pub fn inspect_pack(dir: &Path, opts: &LoadOptions<'_>) -> Result<LoadedPack, LoadError> {
    let manifest = crate::manifest::load(&dir.join("pack.toml"))?;
    let name = manifest.pack.name.clone();
    let dir_name = dir
        .file_name()
        .and_then(gob_path::exact_text)
        .unwrap_or_default();
    if dir_name != name {
        return Err(PackError::malformed(
            &gob_path::Shown::with_home(dir, None).to_string(),
            "pack.name",
            format!("`{name}` must match its directory name `{dir_name}`"),
        )
        .into());
    }
    let provenance = Provenance::Repo.label(&name);
    let tree = tree_digest(dir, &[])?;

    let content = match &manifest.provides.atoms {
        Some(atoms) => {
            let (afile, atext) = read::read_text(dir, atoms, "provides.atoms")?;
            let tpl = match &manifest.provides.templates {
                Some(t) => Some(read::read_text(dir, t, "provides.templates")?),
                None => None,
            };
            let tpl_ref = tpl.as_ref().map(|(f, t)| (f.as_str(), t.as_str()));
            Some(tier1::parse(&name, &afile, &atext, tpl_ref)?)
        }
        None => None,
    };

    let (plans, source) = if manifest.provides.rules.is_empty() {
        (Vec::new(), Source::Compiled)
    } else {
        let files = read::expand(dir, &manifest.provides.rules, "provides.rules")?;
        match opts.cache {
            Some((cache, engine)) => {
                let l = cache.load_or_compile(&tree, engine, || compile_rules(dir, &files))?;
                (l.plans, l.source)
            }
            None => (compile_rules(dir, &files)?, Source::Compiled),
        }
    };

    let locked = snapshot(&manifest, content.as_ref(), &tree);
    let (findings, lock_verified) = match opts.lock {
        Some(lock) => {
            let mut mine = lock.clone();
            mine.pack.retain(|p| p.name == name);
            let f = verify(&mine, std::slice::from_ref(&locked));
            let ok = f.is_empty();
            (f, ok)
        }
        None => (Vec::new(), false),
    };

    let unavailable = if manifest.provides.wasm.is_empty() {
        Vec::new()
    } else {
        tracing::warn!(pack = %name, components = manifest.provides.wasm.len(), "tier-3 content refused");
        vec![Unavailable {
            pack: name.clone(),
            provenance: provenance.clone(),
            families: manifest.pack.families.clone(),
            components: manifest.provides.wasm.clone(),
            reason: TIER3_REASON.to_owned(),
        }]
    };

    Ok(LoadedPack {
        manifest,
        provenance,
        content,
        plans,
        source,
        tree,
        locked,
        findings,
        lock_verified,
        unavailable,
    })
}
