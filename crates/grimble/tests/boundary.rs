//! grimble never depends on a frob crate (boundaries.md): walk every grimble crate's path
//! dependencies transitively and fail on any `frob-*` crate.

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

/// Names and manifests of the path dependencies of the manifest at `manifest`.
fn path_dependencies(manifest: &Path) -> Vec<(String, PathBuf)> {
    let text = std::fs::read_to_string(manifest).expect("read manifest");
    let table: toml::Table = text.parse().expect("valid manifest");
    let dir = manifest.parent().expect("manifest dir");
    table
        .get("dependencies")
        .and_then(toml::Value::as_table)
        .into_iter()
        .flatten()
        .filter_map(|(name, spec)| {
            let path = spec.as_table()?.get("path")?.as_str()?;
            Some((name.clone(), dir.join(path).join("Cargo.toml")))
        })
        .collect()
}

// frob:tests crates/grimble/src/lib.rs::cli
#[test]
fn no_frob_crate_is_a_direct_or_transitive_dependency_of_a_grimble_crate() {
    let crates = Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let mut roots: Vec<(String, PathBuf)> = std::fs::read_dir(&crates)
        .expect("read crates dir")
        .filter_map(Result::ok)
        .filter(|e| e.file_name().to_string_lossy().starts_with("grimble"))
        .map(|e| {
            (
                e.file_name().to_string_lossy().into_owned(),
                e.path().join("Cargo.toml"),
            )
        })
        .filter(|(_, m)| m.is_file())
        .collect();
    assert!(
        roots.iter().any(|(n, _)| n == "grimble")
            && roots.iter().any(|(n, _)| n == "grimble-check"),
        "the walk found the grimble crates: {roots:?}"
    );
    let mut seen: BTreeSet<String> = BTreeSet::new();
    let mut offenders = Vec::new();
    while let Some((name, manifest)) = roots.pop() {
        if !seen.insert(name.clone()) {
            continue;
        }
        if name.starts_with("frob") {
            offenders.push(name.clone());
        }
        roots.extend(path_dependencies(&manifest));
    }
    assert!(
        offenders.is_empty(),
        "grimble crates depend on frob crates: {offenders:?}"
    );
}
