//! gob-check serves frob and grimble alike, so it must not depend on any frob crate.

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

/// Names of the path dependencies declared in `[dependencies]` of the manifest at `manifest`.
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

// frob:tests crates/gob-check/src/lib.rs::run
#[test]
fn no_frob_crate_is_a_direct_or_transitive_dependency() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("Cargo.toml");
    let mut seen: BTreeSet<String> = BTreeSet::new();
    let mut queue = path_dependencies(&root);
    while let Some((name, manifest)) = queue.pop() {
        if !seen.insert(name) {
            continue;
        }
        queue.extend(path_dependencies(&manifest));
    }
    assert!(
        !seen.is_empty(),
        "the walk found the workspace dependencies"
    );
    let frob: Vec<_> = seen.iter().filter(|n| n.starts_with("frob")).collect();
    assert!(
        frob.is_empty(),
        "gob-check depends on frob crates: {frob:?}"
    );
}
