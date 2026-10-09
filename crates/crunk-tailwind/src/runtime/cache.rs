//! The result cache: one entry per (Tailwind version, config content) holding every candidate
//! resolved so far, merged on write.
//!
//! A project with hundreds of distinct classes would otherwise spread across hundreds of keys;
//! one universe per config generation keeps a warm run a single read and a single write. The key
//! hashes the config and CSS entry **and the relative files they pull in** (`@import`, `@config`,
//! `import ... from "./x"`, `require("./x")`, to a bounded depth), so regenerating a theme JSON
//! that the config imports invalidates the entry.

// frob:ticket 01M43ARYX61ESX3S9XG1WS0DQ4

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

use gob_cache::{ArtifactKey, Cache};
use gob_walk::Digest;
use serde::{Deserialize, Serialize};

use super::model::{ClassResult, TailwindVersion};

/// Producer identity of the universe entries; bump to invalidate every stored entry.
pub const PRODUCER: &str = "crunk-tailwind-runtime/universe-1";

/// How many levels of relative imports the source closure follows.
const MAX_DEPTH: usize = 6;

/// Extensions tried for an extension-less relative import.
const EXTENSIONS: [&str; 7] = ["", ".ts", ".js", ".mjs", ".cjs", ".json", ".css"];

/// Every candidate resolved so far for one config generation.
#[derive(Debug, Default, Serialize, Deserialize)]
pub(crate) struct Universe {
    /// Results by candidate.
    pub classes: BTreeMap<String, ClassResult>,
}

/// The key of the universe for `version` and the content of `sources` (and what they import).
pub(crate) fn universe_key(version: TailwindVersion, sources: &[PathBuf]) -> ArtifactKey {
    let mut material = Vec::new();
    material.extend_from_slice(PRODUCER.as_bytes());
    material.extend_from_slice(&version.major().to_le_bytes());
    for path in source_closure(sources) {
        material.extend_from_slice(path.to_string_lossy().as_bytes());
        match std::fs::read(&path) {
            Ok(bytes) => material.extend_from_slice(&bytes),
            Err(e) => {
                tracing::debug!(path = %path.display(), error = %e, "unreadable cache source hashes as empty");
            }
        }
    }
    ArtifactKey {
        content_digest: Digest::of(&material).to_string(),
        producer_identity: PRODUCER.to_owned(),
    }
}

/// Read the universe under `key`; a miss or an undecodable entry is an empty universe.
pub(crate) fn load(cache: &Cache, key: &ArtifactKey) -> Universe {
    cache
        .get_artifact(key)
        .and_then(|bytes| serde_json::from_slice(&bytes).ok())
        .unwrap_or_default()
}

/// Store `universe` under `key` (best effort).
pub(crate) fn store(cache: &Cache, key: &ArtifactKey, universe: &Universe) {
    match serde_json::to_vec(universe) {
        Ok(bytes) => cache.put_artifact(key, &bytes),
        Err(e) => tracing::warn!(error = %e, "cannot encode the tailwind cache entry"),
    }
}

/// `sources` plus every existing relative file they reference, transitively, sorted.
fn source_closure(sources: &[PathBuf]) -> BTreeSet<PathBuf> {
    let mut seen: BTreeSet<PathBuf> = BTreeSet::new();
    let mut frontier: Vec<PathBuf> = sources.to_vec();
    for _ in 0..=MAX_DEPTH {
        let mut next = Vec::new();
        for path in frontier {
            if !seen.insert(path.clone()) {
                continue;
            }
            let Ok(text) = std::fs::read_to_string(&path) else {
                continue;
            };
            let dir = path.parent().unwrap_or(Path::new("."));
            for spec in relative_specifiers(&text) {
                if let Some(found) = resolve_relative(dir, &spec) {
                    next.push(found);
                }
            }
        }
        if next.is_empty() {
            break;
        }
        frontier = next;
    }
    seen
}

/// Every quoted string in `text` that starts with `./` or `../`.
pub(crate) fn relative_specifiers(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let bytes = text.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        let q = bytes[i];
        if q == b'"' || q == b'\'' || q == b'`' {
            let start = i + 1;
            if let Some(len) = text[start..].find(q as char) {
                let inner = &text[start..start + len];
                if (inner.starts_with("./") || inner.starts_with("../")) && !inner.contains('\n') {
                    out.push(inner.to_owned());
                }
                i = start + len + 1;
                continue;
            }
        }
        i += 1;
    }
    out
}

fn resolve_relative(dir: &Path, spec: &str) -> Option<PathBuf> {
    let base = dir.join(spec);
    EXTENSIONS
        .iter()
        .map(|ext| PathBuf::from(format!("{}{ext}", base.display())))
        .find(|p| p.is_file())
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-tailwind/src/runtime/cache.rs::relative_specifiers
    #[test]
    fn relative_specifiers_find_quoted_relative_paths_only() {
        let text = r#"import t from "./tailwind.theme.json"; const x = require('../a/b'); @import "tailwindcss"; "not/relative""#;
        assert_eq!(
            relative_specifiers(text),
            ["./tailwind.theme.json", "../a/b"]
        );
    }

    // frob:tests crates/crunk-tailwind/src/runtime/cache.rs::universe_key
    #[test]
    fn the_key_changes_when_an_imported_file_changes() {
        let dir = tempfile::tempdir().unwrap();
        let config = dir.path().join("tailwind.config.ts");
        let theme = dir.path().join("theme.json");
        std::fs::write(&config, "import theme from \"./theme.json\";").unwrap();
        std::fs::write(&theme, "{\"a\":1}").unwrap();
        let before = universe_key(TailwindVersion::V4, std::slice::from_ref(&config));
        std::fs::write(&theme, "{\"a\":2}").unwrap();
        let after = universe_key(TailwindVersion::V4, std::slice::from_ref(&config));
        assert_ne!(before, after);
        let other_version = universe_key(TailwindVersion::V3, std::slice::from_ref(&config));
        assert_ne!(after, other_version);
    }
}
