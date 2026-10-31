//! Repository packs, tier 1 (atoms, callee vocabularies and detector rows): `packs/NAME.toml` for each `local/NAME` in `[packs] enabled`.
//!
//! The minimal slice of the pack loader (packs.md 3.3): the file is parsed for its `[pack]`
//! version, its `[[atom]]` names, its `[[vocab]]` classes and its `[[detector]]` rows (kinds
//! `callee`, `none` and `impossible`; other kinds are logged and left as no detector), and handed to the model rules as a
//! [`PackPin`]. The lock, the other tiers, templates and external packs stay with the full
//! loader. Built-in `grimble/...` packs have no file here and stay unloaded (their atoms are compiled into the registry).

// frob:ticket 01M4FGXVQTN5NJ0JBGWAMVHK82
// frob:ticket 01M4HEMAM737MTY3385G7VKXQ4
// frob:ticket 01M61Y35AKW4QDRE70W6HFQAJ5

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use grimble_model::args::ArgKind;
use grimble_model::{PackDetector, PackDetectorKind, PackPin};
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
    #[serde(default)]
    vocab: Vec<VocabRow>,
    #[serde(default)]
    detector: Vec<DetectorRow>,
}

#[derive(Deserialize)]
struct PackHeader {
    version: String,
}

#[derive(Deserialize)]
struct AtomRow {
    name: String,
    /// `none` (the default), `path`, `host`, `name` or `string`: what `may ATOM(\"..\")` constrains.
    #[serde(default)]
    args: Option<String>,
}

#[derive(Deserialize)]
struct VocabRow {
    lang: String,
    class: String,
    #[serde(default)]
    names: Vec<String>,
}

#[derive(Deserialize)]
struct DetectorRow {
    atom: Option<String>,
    #[serde(default)]
    atoms: Option<AtomsSel>,
    lang: Option<String>,
    #[serde(default)]
    langs: Vec<String>,
    kind: String,
    /// The vocabulary class of a `callee` row; defaults to the atom's own name.
    vocab: Option<String>,
}

/// `atoms = "*"` or `atoms = [..]` of a detector row.
#[derive(Deserialize)]
#[serde(untagged)]
enum AtomsSel {
    One(String),
    Many(Vec<String>),
}

/// The argument kind each `[[atom]]` row declares through `args`; an unknown value is an error
/// naming the atom. Atoms with `none` or no `args` are left out (they take no arguments).
fn arg_kinds_of(rows: &[AtomRow]) -> Result<BTreeMap<String, ArgKind>, String> {
    let mut out = BTreeMap::new();
    for row in rows {
        let Some(raw) = row.args.as_deref() else {
            continue;
        };
        match ArgKind::from_pack_args(raw) {
            Ok(Some(kind)) => {
                out.insert(row.name.clone(), kind);
            }
            Ok(None) => {}
            Err(why) => return Err(format!("atom `{}`: {why}", row.name)),
        }
    }
    Ok(out)
}

/// Expand the detector rows of a pack file into one [`PackDetector`] per `(atom, language)`.
///
/// `atoms = "*"` is every atom of the pack. A `callee` row's names are the union of the `[[vocab]]`
/// rows of its class and language; query, attribute and pattern rows are not executable by this
/// build and are skipped (the cell stays Unknown, which the capability rules report).
fn expand_detectors(file: &PackFile, atoms: &BTreeSet<String>) -> Vec<PackDetector> {
    let mut out = Vec::new();
    for row in &file.detector {
        let kind = match row.kind.as_str() {
            "callee" => PackDetectorKind::Callee,
            "none" => PackDetectorKind::None,
            "impossible" => PackDetectorKind::Impossible,
            other => {
                tracing::warn!(
                    kind = other,
                    "pack detector kind is not executable here; no detector"
                );
                continue;
            }
        };
        let names_atoms: Vec<String> = match (&row.atom, &row.atoms) {
            (Some(a), _) => vec![a.clone()],
            (None, Some(AtomsSel::One(s))) if s == "*" => atoms.iter().cloned().collect(),
            (None, Some(AtomsSel::One(s))) => vec![s.clone()],
            (None, Some(AtomsSel::Many(v))) => v.clone(),
            (None, None) => {
                tracing::warn!("pack detector row names no atom; skipped");
                continue;
            }
        };
        let langs: Vec<String> = row
            .lang
            .iter()
            .cloned()
            .chain(row.langs.iter().cloned())
            .collect();
        for atom in names_atoms {
            for lang in &langs {
                let class = row.vocab.as_deref().unwrap_or(&atom);
                let names: BTreeSet<String> = if kind == PackDetectorKind::Callee {
                    file.vocab
                        .iter()
                        .filter(|v| v.class == class && &v.lang == lang)
                        .flat_map(|v| v.names.iter().cloned())
                        .collect()
                } else {
                    BTreeSet::new()
                };
                out.push(PackDetector {
                    atom: atom.clone(),
                    lang: lang.clone(),
                    kind,
                    names,
                });
            }
        }
    }
    out
}

/// Load every enabled `local/NAME` pack of `table` from `<root>/packs/NAME.toml`.
#[allow(
    clippy::disallowed_methods,
    reason = "pack files live under the packs state dir, outside the walk"
)]
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
                let atoms: BTreeSet<String> = file.atom.iter().map(|a| a.name.clone()).collect();
                let arg_kinds = match arg_kinds_of(&file.atom) {
                    Ok(k) => k,
                    Err(why) => {
                        tracing::warn!(%id, path = %rel, %why, "pack atom declares a bad args kind");
                        out.problems
                            .insert(id.clone(), format!("`{rel}` is malformed ({why})"));
                        continue;
                    }
                };
                let detectors = expand_detectors(&file, &atoms);
                tracing::info!(%id, path = %rel, atoms = atoms.len(), detectors = detectors.len(), version = %file.pack.version, "repository pack loaded");
                out.sources
                    .insert(id.clone(), format!("repo:{PACKS_DIR}/{name}"));
                out.pins.insert(
                    id.clone(),
                    PackPin {
                        version: file.pack.version,
                        digest: Some(blake3_tagged(&bytes)),
                        atoms,
                        arg_kinds,
                        detectors,
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
