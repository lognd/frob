//! Ratchet: every `#[rule(id = ...)]` declaration in the workspace names a distinct id (R2).
#![allow(
    clippy::disallowed_methods,
    reason = "a workspace-wide source scan reads the disk, not a walked Core"
)]

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

/// Collect every `.rs` file under a crate's `src` directory.
fn rust_sources(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            rust_sources(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

/// The ids declared by `#[rule(` attributes in one source text.
fn declared_ids(text: &str) -> Vec<String> {
    let mut ids = Vec::new();
    let mut in_rule = false;
    for line in text.lines() {
        let line = line.trim();
        if line.starts_with("#[rule(") {
            in_rule = true;
        }
        if in_rule {
            if let Some(rest) = line.strip_prefix("id = \"")
                && let Some(id) = rest.split('"').next()
            {
                ids.push(id.to_owned());
            }
            if line.ends_with(")]") {
                in_rule = false;
            }
        }
    }
    ids
}

#[test]
fn no_rule_id_is_declared_twice_in_the_workspace() {
    let crates = Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let mut files = Vec::new();
    for entry in fs::read_dir(&crates).expect("crates dir").flatten() {
        rust_sources(&entry.path().join("src"), &mut files);
    }
    let mut seen: BTreeMap<String, Vec<PathBuf>> = BTreeMap::new();
    for file in &files {
        let text = fs::read_to_string(file).unwrap_or_default();
        for id in declared_ids(&text) {
            seen.entry(id).or_default().push(file.clone());
        }
    }
    assert!(
        seen.len() > 50,
        "scan found too few declarations: {}",
        seen.len()
    );
    let dupes: Vec<_> = seen.iter().filter(|(_, f)| f.len() > 1).collect();
    assert!(
        dupes.is_empty(),
        "rule ids declared more than once: {dupes:#?}"
    );
}
