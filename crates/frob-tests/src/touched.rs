//! The touched set: files changed against a base and the symbols inside them that changed.

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use gob_cache::Cache;
use gob_git::{Repo, TreeRef};
use gob_rules::{Finding, Rule, RuleId, Severity};
use gob_symbols::{
    Digests, FileSymbols, SymbolGraph, Symref, Target, adapter_for_path, build_graph, extract_file,
};
use gob_walk::{Digest, FileEntry, LanguageHint, WalkConfig, walk};
use schemars::JsonSchema;
use serde::Serialize;

use crate::error::Result;
use crate::rule::Test001;

/// Changed files and changed symbols (the seeds of test selection).
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, JsonSchema)]
pub struct TouchedSet {
    /// Repo-relative paths that differ between the base and the work tree.
    pub files: Vec<String>,
    /// Symbols of the current graph that are new or whose signature or body digest changed.
    #[schemars(with = "Vec<String>")]
    pub symbols: Vec<Symref>,
    /// Changed files no adapter reads (G18): test selection cannot say what they affect.
    pub unresolved_files: Vec<String>,
}

impl TouchedSet {
    /// One Unresolved `TEST001` finding when changed files have no adapter; empty otherwise.
    ///
    /// Silently ignoring such a file would select too few tests, so the
    /// selection is reported undecided for them instead.
    pub fn selection_findings(&self) -> Vec<Finding> {
        let Some(first) = self.unresolved_files.first() else {
            return Vec::new();
        };
        let id: RuleId = Test001
            .meta()
            .rule_id()
            .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"));
        vec![Finding::new(
            id,
            Severity::Unresolved,
            None,
            format!(
                "test selection is undecided for {} changed file(s) with no adapter (first `{first}`)",
                self.unresolved_files.len()
            ),
            "selection:no-adapter",
        )]
    }
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
    let unresolved_files: Vec<String> = files
        .iter()
        // frob:ticket 01M43A5DJT8XBQYEK36F0KSGKF
        // frob:todo 01M43A5MA7GRAACT7E0M525Y1M Python files stay unresolved until pytest selection lands.
        .filter(|p| adapter_for_path(p).is_none() || gob_symbols::is_python_path(p))
        .cloned()
        .collect();
    for p in &unresolved_files {
        tracing::info!(path = %p, "changed file has no adapter: test selection unresolved");
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
        unresolved_files,
    })
}
