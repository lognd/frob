//! Repository packs, tier 1 (atoms only): `packs/NAME.toml` for each `local/NAME` in `[packs] enabled`.
//!
//! The minimal slice of the pack loader (packs.md 3.3): the file is parsed for its `[pack]`
//! version and its `[[atom]]` names, and handed to the model rules as a
//! [`PackPin`]. The lock, the other tiers, templates and external packs stay with the full
//! loader. Built-in `grimble/...` packs have no file here and stay unloaded (their atoms are compiled into the registry).

// frob:ticket 01M4FGXVQTN5NJ0JBGWAMVHK82

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use grimble_model::PackPin;
use serde::Deserialize;

use crate::config::{PacksTable, blake3_tagged};

/// Directory of repository packs, relative to the repository root.
pub const PACKS_DIR: &str = "packs";

/// What loading the enabled packs produced.
#[derive(Debug, Default)]
pub struct LoadedPacks {
    /// Loaded packs by id, for the model rules.
    pub pins: BTreeMap<String, PackPin>,
    /// Why an enabled pack could not be loaded, by id.
    pub problems: BTreeMap<String, String>,
    /// Enabled ids this build cannot load (external packs, unknown namespaces).
    pub unsupported: Vec<String>,
    /// Provenance by id, `repo:packs/NAME`.
    pub sources: BTreeMap<String, String>,
}

#[derive(Deserialize)]
struct PackFile {
    pack: PackHeader,
    #[serde(default)]
    atom: Vec<AtomRow>,
}

#[derive(Deserialize)]
struct PackHeader {
    version: String,
}

#[derive(Deserialize)]
struct AtomRow {
    name: String,
}

/// Load every enabled `local/NAME` pack of `table` from `<root>/packs/NAME.toml`.
pub fn load(root: &Path, table: &PacksTable) -> LoadedPacks {
    let mut out = LoadedPacks::default();
    for id in &table.enabled {
        if id.starts_with("grimble/") {
            tracing::debug!(%id, "built-in pack has no file to load");
            continue;
        }
        let Some(name) = id.strip_prefix("local/") else {
            tracing::warn!(%id, "pack namespace is not loadable by this build");
            out.unsupported.push(id.clone());
            continue;
        };
        let rel = format!("{PACKS_DIR}/{name}.toml");
        let bytes = match std::fs::read(root.join(&rel)) {
            Ok(b) => b,
            Err(err) => {
                tracing::warn!(%id, path = %rel, %err, "enabled pack file cannot be read");
                out.problems
                    .insert(id.clone(), format!("`{rel}` cannot be read ({err})"));
                continue;
            }
        };
        let parsed = std::str::from_utf8(&bytes)
            .map_err(|e| e.to_string())
            .and_then(|t| toml::from_str::<PackFile>(t).map_err(|e| e.to_string()));
        match parsed {
            Ok(file) => {
                let atoms: BTreeSet<String> = file.atom.into_iter().map(|a| a.name).collect();
                tracing::info!(%id, path = %rel, atoms = atoms.len(), version = %file.pack.version, "repository pack loaded");
                out.sources
                    .insert(id.clone(), format!("repo:{PACKS_DIR}/{name}"));
                out.pins.insert(
                    id.clone(),
                    PackPin {
                        version: file.pack.version,
                        digest: Some(blake3_tagged(&bytes)),
                        atoms,
                    },
                );
            }
            Err(why) => {
                tracing::warn!(%id, path = %rel, %why, "pack file is malformed");
                out.problems
                    .insert(id.clone(), format!("`{rel}` is malformed ({why})"));
            }
        }
    }
    out
}
