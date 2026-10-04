//! The Cargo adapter: `target/<profile>` and `target/<triple>/<profile>` directories.
//!
//! Units: each `incremental/*` directory; the files of one compilation unit in
//! `deps/` (grouped by name-and-hash stem, so a `.rlib`, `.rmeta` and `.d` go
//! together); each `build/*` script directory. `.fingerprint/` is left (it is
//! small and a stale one only forces a rebuild), as are the profile's top-level
//! binaries. Output of a binary named in `keep_binaries` is never a unit, in
//! `deps/` or elsewhere.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::path::{Path, PathBuf};
use std::time::SystemTime;

use super::adapter::{BuildAdapter, BuildPolicy, Unit, UnitKind};
use super::scan::scan;

/// The Cargo build-output adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct CargoAdapter;

/// True when `p` is a real directory (not a symlink to one).
fn real_dir(p: &Path) -> bool {
    std::fs::symlink_metadata(p).is_ok_and(|m| m.is_dir())
}

/// Child entries of `dir` that are real (non-symlink) entries; symlinks are skipped.
fn children(dir: &Path) -> Vec<PathBuf> {
    let Ok(rd) = std::fs::read_dir(dir) else {
        return Vec::new();
    };
    let mut v: Vec<PathBuf> = rd
        .filter_map(Result::ok)
        .filter(|e| e.file_type().is_ok_and(|t| !t.is_symlink()))
        .map(|e| e.path())
        .collect();
    v.sort();
    v
}

/// True when `dir` looks like a cargo profile directory.
fn is_profile(dir: &Path) -> bool {
    ["deps", "incremental", ".fingerprint"]
        .iter()
        .any(|n| real_dir(&dir.join(n)))
}

/// Every profile directory under a cargo target directory, including per-triple ones.
fn profile_dirs(target: &Path) -> Vec<PathBuf> {
    let mut out = Vec::new();
    for c in children(target).into_iter().filter(|c| real_dir(c)) {
        if is_profile(&c) {
            out.push(c);
        } else {
            out.extend(
                children(&c)
                    .into_iter()
                    .filter(|g| real_dir(g) && is_profile(g)),
            );
        }
    }
    out
}

/// The compilation-unit key of a `deps/` entry: its name up to the first dot, without a `lib` prefix.
fn unit_key(name: &str) -> String {
    let stem = name.split('.').next().unwrap_or(name);
    stem.strip_prefix("lib").unwrap_or(stem).to_owned()
}

/// True when a `deps/` entry belongs to one of the kept binaries (`frob-<hash>`, `frob-<hash>.exe`, ...).
fn is_kept(name: &str, keep: &[String]) -> bool {
    let stem = name.split('.').next().unwrap_or(name);
    let base = stem.rsplit_once('-').map_or(stem, |(b, _)| b);
    keep.iter().any(|k| k == base || k == stem)
}

impl CargoAdapter {
    fn incremental_units(profile: &Path) -> Vec<Unit> {
        children(&profile.join("incremental"))
            .into_iter()
            .map(|p| {
                let s = scan(&p);
                Unit {
                    label: format!("incremental/{}", file_name(&p)),
                    paths: vec![p],
                    kind: UnitKind::Incremental,
                    bytes: s.bytes,
                    modified: s.newest.unwrap_or(SystemTime::UNIX_EPOCH),
                }
            })
            .collect()
    }

    fn dep_units(profile: &Path, keep: &[String]) -> Vec<Unit> {
        let mut groups: std::collections::BTreeMap<String, Unit> =
            std::collections::BTreeMap::new();
        for p in children(&profile.join("deps")) {
            let name = file_name(&p);
            if is_kept(&name, keep) {
                continue;
            }
            let s = scan(&p);
            let key = unit_key(&name);
            let unit = groups.entry(key.clone()).or_insert_with(|| Unit {
                label: format!("deps/{key}"),
                paths: Vec::new(),
                kind: UnitKind::Artifact,
                bytes: 0,
                modified: SystemTime::UNIX_EPOCH,
            });
            unit.paths.push(p);
            unit.bytes = unit.bytes.saturating_add(s.bytes);
            unit.modified = unit
                .modified
                .max(s.newest.unwrap_or(SystemTime::UNIX_EPOCH));
        }
        groups.into_values().collect()
    }

    fn build_units(profile: &Path, keep: &[String]) -> Vec<Unit> {
        children(&profile.join("build"))
            .into_iter()
            .filter(|p| real_dir(p) && !is_kept(&file_name(p), keep))
            .map(|p| {
                let s = scan(&p);
                Unit {
                    label: format!("build/{}", file_name(&p)),
                    paths: vec![p],
                    kind: UnitKind::Artifact,
                    bytes: s.bytes,
                    modified: s.newest.unwrap_or(SystemTime::UNIX_EPOCH),
                }
            })
            .collect()
    }
}

fn file_name(p: &Path) -> String {
    p.file_name()
        .map_or_else(String::new, |n| n.to_string_lossy().into_owned())
}

impl BuildAdapter for CargoAdapter {
    fn name(&self) -> &'static str {
        "cargo"
    }

    fn output_dirs(&self, checkout: &Path) -> Vec<PathBuf> {
        let target = checkout.join("target");
        if real_dir(&target) {
            vec![target]
        } else {
            Vec::new()
        }
    }

    fn units(&self, dir: &Path, policy: &BuildPolicy) -> Vec<Unit> {
        let mut units = Vec::new();
        for profile in profile_dirs(dir) {
            units.extend(Self::incremental_units(&profile));
            units.extend(Self::dep_units(&profile, &policy.keep_binaries));
            units.extend(Self::build_units(&profile, &policy.keep_binaries));
        }
        tracing::debug!(dir = %dir.display(), units = units.len(), "cargo units listed");
        units
    }
}
