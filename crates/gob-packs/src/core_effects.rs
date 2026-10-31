//! The `core-effects` pack as versioned data: its lock entry (packs.md 8.1).
//!
//! The manifest and atoms live under `packs/core-effects` and are embedded by `gob_ir::core_pack`,
//! which serves them to the registry. This module derives the lock entry from those same bytes,
//! so the version recorded in `grimble.packs.lock` and any change to the vocabulary are checked
//! against exactly what the binary runs: a vocabulary change without a version bump is a PACK001
//! `ItemChangedWithoutBump` finding from [`crate::lock::verify`].

// frob:ticket 01M5XNNHV9M8HCP76TD867GGVJ

use gob_ir::core_pack::{ATOMS_TOML, OWNER, PACK_TOML};

use crate::lock::{LockedPack, snapshot};
use crate::tier1::{self, Tier1Error};
use crate::{Digest, Manifest, PackError};

/// The label used for the embedded manifest in error messages.
pub const FILE: &str = "<builtin>/core-effects/pack.toml";
/// The label used for the embedded atoms file in error messages.
pub const ATOMS_FILE: &str = "<builtin>/core-effects/atoms.toml";

/// Why the embedded core-effects pack could not be turned into a lock entry (a build defect).
#[derive(Debug, thiserror::Error)]
pub enum CoreEffectsError {
    /// The embedded manifest is malformed.
    #[error(transparent)]
    Manifest(#[from] PackError),
    /// The embedded atoms file is malformed.
    #[error(transparent)]
    Atoms(#[from] Tier1Error),
}

/// Parses the embedded manifest.
///
/// # Errors
/// PACK005 if the embedded manifest is malformed.
pub fn manifest() -> Result<Manifest, PackError> {
    Manifest::parse(FILE, PACK_TOML)
}

/// The digest of the embedded pack bytes: manifest text and atoms text, length-prefixed.
pub fn digest() -> Digest {
    let mut h = blake3::Hasher::new();
    for (name, text) in [("pack.toml", PACK_TOML), ("atoms.toml", ATOMS_TOML)] {
        h.update(name.as_bytes());
        h.update(&(text.len() as u64).to_le_bytes());
        h.update(text.as_bytes());
    }
    *h.finalize().as_bytes()
}

/// The core-effects lock entry: version from the manifest, items from the atoms file.
///
/// # Errors
/// [`CoreEffectsError`] if either embedded file is malformed.
pub fn locked() -> Result<LockedPack, CoreEffectsError> {
    let m = manifest()?;
    let content = tier1::parse(OWNER, ATOMS_FILE, ATOMS_TOML, None)?;
    let pack = snapshot(&m, Some(&content), &digest());
    tracing::debug!(
        version = %pack.version,
        items = pack.items.len(),
        "core-effects lock entry built"
    );
    Ok(pack)
}
