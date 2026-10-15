//! The `std` pack: the binary's own rules as a pack like any other (plugins.md sections 2, 6.1, 11.2).
//!
//! Its GRL sources live under `packs/std`; the compiled plans are embedded with
//! `include_bytes!`. Hand-written tier-0 Rust rules are recorded as known exceptions
//! (every row of the parity table but "source"). The lock entry is frozen to the binary:
//! the manifest version is stamped with this crate's version and the tree digest covers
//! the manifest text, the version and every embedded plan, so it changes only with the binary.

// frob:ticket 01M3ZX7FYE5D1N2SY01VNVVACK

use std::collections::BTreeMap;

use gob_plan::plan::{Plan, PlanError};
use serde::Serialize;

use crate::lock::{LockedPack, item_digest, snapshot};
use crate::{Digest, Manifest, PackError, check_unique, to_hex};

/// The pack name std registers under.
pub const NAME: &str = "std";
/// The label used for std in error messages (it has no file on disk).
pub const FILE: &str = "<builtin>/std/pack.toml";

const MANIFEST_TEXT: &str = include_str!("../../../../packs/std/pack.toml");

/// Embedded GRL-compiled plans by rule id, in source order.
static PLANS: [(&str, &[u8]); 1] = [(
    "TODO001",
    include_bytes!("../../../../packs/std/plans/TODO001.plan"),
)];

/// Families whose rules are hand-written Rust (tier 0), recorded as known exceptions.
pub const KNOWN_EXCEPTIONS: [&str; 25] = [
    "AFFECT", "CAP", "CFG", "CI", "COV", "DOC", "DRIFT", "DSL", "EXC", "GRL", "INV", "MDL",
    "PARSE", "PERF", "PM", "PROC", "READ", "REF", "REL", "SCOPE", "SIB", "SYS", "TEST", "TICK",
    "TOOL",
];

/// Where a listed pack came from.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum PackSource {
    /// Compiled into the binary.
    Builtin,
}

/// The `packs list --json` row for std.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct StdEntry {
    /// The pack name (`std`).
    pub name: String,
    /// The binary's version.
    pub version: String,
    /// Always [`PackSource::Builtin`].
    pub source: PackSource,
    /// The `blake3:` digest frozen to the binary.
    pub digest: String,
    /// Families std owns.
    pub families: Vec<String>,
    /// Families whose rules are hand-written Rust, not GRL.
    pub known_exceptions: Vec<String>,
}

/// Parses the embedded manifest and stamps this binary's version on it.
///
/// # Errors
/// PACK005 if the embedded manifest is malformed (a build defect, never user input).
pub fn manifest() -> Result<Manifest, PackError> {
    let mut m = Manifest::parse(FILE, MANIFEST_TEXT)?;
    env!("CARGO_PKG_VERSION").clone_into(&mut m.pack.version);
    Ok(m)
}

/// Decodes the embedded plans, in source order.
///
/// # Errors
/// [`PlanError`] if an embedded plan is structurally malformed (a build defect).
pub fn plans() -> Result<Vec<Plan>, PlanError> {
    PLANS.iter().map(|(_, b)| Plan::load_embedded(b)).collect()
}

/// The digest frozen to the binary: manifest text, version and every embedded plan.
pub fn digest() -> Digest {
    let mut h = blake3::Hasher::new();
    h.update(MANIFEST_TEXT.as_bytes());
    h.update(env!("CARGO_PKG_VERSION").as_bytes());
    for (id, bytes) in &PLANS {
        h.update(id.as_bytes());
        h.update(&(bytes.len() as u64).to_le_bytes());
        h.update(bytes);
    }
    *h.finalize().as_bytes()
}

/// The std lock entry: tree digest frozen to the binary, one `plan:ID` item per embedded plan.
///
/// # Errors
/// PACK005 if the embedded manifest is malformed.
pub fn locked() -> Result<LockedPack, PackError> {
    let mut pack = snapshot(&manifest()?, None, &digest());
    let items: &mut BTreeMap<String, String> = &mut pack.items;
    for (id, bytes) in &PLANS {
        let canon = format!("{id}:{}", to_hex(blake3::hash(bytes).as_bytes()));
        items.insert(format!("plan:{id}"), item_digest(&canon));
    }
    tracing::debug!(items = pack.items.len(), "std lock entry built");
    Ok(pack)
}

/// The `packs list` entry for std: builtin source, frozen digest, known exceptions.
///
/// # Errors
/// PACK005 if the embedded manifest is malformed.
pub fn entry() -> Result<StdEntry, PackError> {
    let m = manifest()?;
    Ok(StdEntry {
        name: m.pack.name,
        version: m.pack.version,
        source: PackSource::Builtin,
        digest: format!("blake3:{}", to_hex(&digest())),
        families: m.pack.families,
        known_exceptions: KNOWN_EXCEPTIONS.iter().map(|s| (*s).to_owned()).collect(),
    })
}

/// Checks a plugin manifest against std: PACK004 when it reuses std's name or a std family.
///
/// # Errors
/// PACK004 naming std and the plugin; PACK005 if the embedded manifest is malformed.
pub fn check_plugin(file: &str, plugin: &Manifest) -> Result<(), PackError> {
    let std = manifest()?;
    tracing::debug!(file, pack = %plugin.pack.name, "checking plugin pack against std");
    check_unique(&[(FILE, &std), (file, plugin)])
}
