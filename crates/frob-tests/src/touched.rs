//! The touched set: files changed against a base and the symbols inside them that changed.

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use gob_cache::Cache;
use gob_git::{Repo, TreeRef};
use gob_rules::{Finding, Rule, RuleId, Severity};
use gob_symbols::{
    BuildStats, Digests, FileSymbols, SymbolGraph, SymbolKind, SymbolRecord, Symref, Target, adapter_for_path,
    build_graph_with_stats, extract_file,
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

/// State directory whose shared cache holds the per-file symbol artifacts.
const STATE_DIR: &str = ".frob";

/// Build the symbol graph of the work tree at `root`, reusing the repository-shared artifact cache.
///
/// # Errors
///
/// [`crate::TestsError::Walk`] for an unusable walk configuration.
pub fn build_repo_graph(root: &Path) -> Result<SymbolGraph> {
    build_repo_graph_with_stats(root).map(|(graph, _)| graph)
}

// frob:ticket 01M4D6NFZGVDDT0GG78KVA1TA6
/// Like [`build_repo_graph`], also returning how many files were extracted versus read from cache.
///
/// # Errors
///
/// [`crate::TestsError::Walk`] for an unusable walk configuration.
pub fn build_repo_graph_with_stats(root: &Path) -> Result<(SymbolGraph, BuildStats)> {
    let walked = walk(root, &WalkConfig::default())?;
    let cache = Cache::open_shared(root, STATE_DIR);
    let (graph, stats) = build_graph_with_stats(root, &walked.files, &cache);
    tracing::info!(
        files = walked.files.len(),
        nodes = graph.node_count(),
        extracted = stats.extracted,
        cached = stats.cached,
        "repository graph built"
    );
    Ok((graph, stats))
}

fn is_rust(path: &str) -> bool {
    Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("rs"))
}

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
// frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6
/// True for the files whose symbols seed selection: Rust, Python and C# sources.
fn is_seed_source(path: &str) -> bool {
    is_rust(path) || gob_symbols::is_python_path(path) || gob_symbols::is_csharp_path(path)
}

// frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6
/// True when `rec` is a C# namespace or type whose own signature is unchanged since `before`.
///
/// Its body digest covers every member, but each member is a symbol of its own, so a changed member
/// is already a seed; seeding the container too would widen to every method of the file.
fn only_members_changed(rec: &SymbolRecord, before: Option<&Digests>) -> bool {
    gob_symbols::is_csharp_path(rec.symref.path())
        && matches!(
            rec.kind,
            SymbolKind::Namespace
                | SymbolKind::Class
                | SymbolKind::Interface
                | SymbolKind::Record
                | SymbolKind::Struct
        )
        && before.is_some_and(|d| d.sig == rec.digests.sig)
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
/// A symbol is touched when it is new in a changed Rust, Python or C# file or its signature or
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
    for path in files.iter().filter(|p| is_seed_source(p)) {
        let before = base_symbols(repo, base, path)?;
        for rec in graph.records().filter(|r| r.symref.path() == path) {
            if !matches!(rec.symref.target(), Target::Symbol(_)) {
                continue;
            }
            let same = before
                .get(&rec.symref)
                .is_some_and(|d| d.sig == rec.digests.sig && d.body == rec.digests.body);
            // frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6
            if !same && !only_members_changed(rec, before.get(&rec.symref)) {
                symbols.insert(rec.symref.clone());
            }
        }
    }
    let unresolved_files: Vec<String> = files
        .iter()
        .filter(|p| adapter_for_path(p).is_none())
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
