//! The pure model crates must not compile gix: git access reaches them only through gob-walk's
//! reader traits (audit M8). Checked over the resolved `cargo metadata` graph.

// frob:ticket 01M4CTE0GYDX0XW64JRNF2ZMQG

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;
use std::process::Command;

use serde_json::Value;

/// Crates whose non-dev dependency closure must stay free of gix.
const GIX_FREE: &[&str] = &["gob-walk", "gob-ir", "gob-symbols", "grimble-model"];

/// Package id to (name, normal-or-build dependency ids) from `cargo metadata`.
fn graph() -> BTreeMap<String, (String, Vec<String>)> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let cargo = std::env::var_os("CARGO").unwrap_or_else(|| "cargo".into());
    let out = Command::new(cargo)
        .current_dir(root)
        .args(["metadata", "--offline", "--format-version", "1"])
        .output()
        .expect("run cargo metadata");
    assert!(out.status.success(), "cargo metadata failed");
    let meta: Value = serde_json::from_slice(&out.stdout).expect("metadata json");
    let names: BTreeMap<&str, &str> = meta["packages"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| (p["id"].as_str().unwrap(), p["name"].as_str().unwrap()))
        .collect();
    meta["resolve"]["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .map(|n| {
            let id = n["id"].as_str().unwrap();
            let deps = n["deps"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|d| {
                    d["dep_kinds"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .any(|k| k["kind"].is_null() || k["kind"] == "build")
                })
                .map(|d| d["pkg"].as_str().unwrap().to_owned())
                .collect();
            (id.to_owned(), (names[id].to_owned(), deps))
        })
        .collect()
}

/// Names of every package reachable from the package called `start` over normal and build edges.
fn closure(g: &BTreeMap<String, (String, Vec<String>)>, start: &str) -> BTreeSet<String> {
    let mut stack: Vec<&String> = g
        .iter()
        .filter(|(_, (name, _))| name == start)
        .map(|(id, _)| id)
        .collect();
    assert!(!stack.is_empty(), "{start} not in the workspace graph");
    let mut seen = BTreeSet::new();
    let mut names = BTreeSet::new();
    while let Some(id) = stack.pop() {
        if !seen.insert(id) {
            continue;
        }
        let (name, deps) = &g[id];
        names.insert(name.clone());
        stack.extend(deps);
    }
    names
}

// frob:tests crates/gob-walk/src/content.rs::ContentSource.locate
#[test]
fn model_crates_do_not_depend_on_gix() {
    let g = graph();
    for krate in GIX_FREE {
        let hits: Vec<String> = closure(&g, krate)
            .into_iter()
            .filter(|n| n == "gix" || n.starts_with("gix-") || n == "gob-git")
            .collect();
        assert!(hits.is_empty(), "{krate} depends on git crates: {hits:?}");
    }
}
