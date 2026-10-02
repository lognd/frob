//! The touched set: files changed against a base and the symbols inside them that changed.

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use gob_cache::Cache;
use gob_git::{Repo, TreeRef};
use gob_symbols::{Digests, FileSymbols, SymbolGraph, Symref, Target, build_graph, extract_file};
use gob_walk::{Digest, FileEntry, LanguageHint, WalkConfig, walk};
use schemars::JsonSchema;
use serde::Serialize;

use crate::error::Result;

/// Changed files and changed symbols (the seeds of test selection).
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, JsonSchema)]
pub struct TouchedSet {
    /// Repo-relative paths that differ between the base and the work tree.
    pub files: Vec<String>,
    /// Symbols of the current graph that are new or whose signature or body digest changed.
    #[schemars(with = "Vec<String>")]
    pub symbols: Vec<Symref>,
}

/// Build the symbol graph of the work tree at `root` (no cache; the tree is the input).
///
/// # Errors
///
/// [`crate::TestsError::Walk`] for an unusable walk configuration.
pub fn build_repo_graph(root: &Path) -> Result<SymbolGraph> {
    let walked = walk(root, &WalkConfig::default())?;
    let graph = build_graph(root, &walked.files, &Cache::null());
    tracing::info!(
        files = walked.files.len(),
        nodes = graph.node_count(),
        "repository graph built"
    );
    Ok(graph)
}

fn is_rust(path: &str) -> bool {
    Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("rs"))
}

fn base_symbols(repo: &Repo, base: &str, path: &str) -> Result<BTreeMap<Symref, Digests>> {
    let Some(bytes) = repo.read_blob_at(base, path)? else {
        return Ok(BTreeMap::new());
    };
    let Ok(text) = String::from_utf8(bytes) else {
        return Ok(BTreeMap::new());
    };
    let entry = FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    let FileSymbols { symbols, .. } = extract_file(&entry, &text);
    Ok(symbols.into_iter().map(|s| (s.symref, s.digests)).collect())
}

/// Files changed between `base` and the work tree, and the changed symbols among `graph`'s.
///
/// A symbol is touched when it is new in a changed Rust file or its signature or
/// body digest differs from the same symref at `base`. Deleted symbols cannot be
/// seeds (they are gone from the graph); their callers are still touched by
/// the edits that removed the calls.
///
/// # Errors
///
/// [`crate::TestsError::Git`] when `base` does not resolve or a diff fails.
pub fn touched_set(repo: &Repo, graph: &SymbolGraph, base: &str) -> Result<TouchedSet> {
    let changed = repo.diff_names(&TreeRef::Ref(base.to_owned()), &TreeRef::WorkTree)?;
    let files: Vec<String> = changed.iter().map(|c| c.path.clone()).collect();
    let mut symbols: BTreeSet<Symref> = BTreeSet::new();
    for path in files.iter().filter(|p| is_rust(p)) {
        let before = base_symbols(repo, base, path)?;
        for rec in graph.records().filter(|r| r.symref.path() == path) {
            if !matches!(rec.symref.target(), Target::Symbol(_)) {
                continue;
            }
            let same = before
                .get(&rec.symref)
                .is_some_and(|d| d.sig == rec.digests.sig && d.body == rec.digests.body);
            if !same {
                symbols.insert(rec.symref.clone());
            }
        }
    }
    tracing::info!(
        base,
        files = files.len(),
        symbols = symbols.len(),
        "touched set computed"
    );
    Ok(TouchedSet {
        files,
        symbols: symbols.into_iter().collect(),
    })
}
