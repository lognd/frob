//! The code side of binding: every walked file folded into a U term and scope graph.

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC
// frob:ticket 01M4D6NGJANPW3T3DKM77B0T1W
// frob:ticket 01M4HW9Y1TXZCN4Y5RF2T7C4A9
// frob:ticket 01M4HB1ZAX0Q6QHK1DK3Y3EZ9E

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, OnceLock};

use gob_cache::{ArtifactKey, Cache};
use gob_ir::{NodeId, Operator, ScopeGraph, Term, Universal};
use gob_symbols::{Adapter, Fidelity, FileSymbols, Folded, adapter_for};

use crate::frob_owned::STATE_DIR;
use gob_walk::{FileEntry, LanguageHint, WalkResult};
use rayon::prelude::*;

/// The tag of a file no adapter claims.
pub const OPAQUE: &str = "opaque";

/// Process-wide count of adapter parses (`fold_file` calls), for the warm-cache counter test.
static ADAPTER_FOLDS: AtomicUsize = AtomicUsize::new(0);

/// How many adapter parses this process has run so far (cache hits do not count).
pub fn adapter_folds() -> usize {
    ADAPTER_FOLDS.load(Ordering::Relaxed)
}

/// Parses and folds one file, counting the parse.
fn counted_fold(e: &FileEntry, text: &str) -> Result<Folded, gob_symbols::FoldError> {
    ADAPTER_FOLDS.fetch_add(1, Ordering::Relaxed);
    gob_symbols::fold_file(e, text)
}

/// One walked file with what folding it produced.
///
/// The cheap per-file facts (symbol view, fidelity, the unseen-remainder flag) come from the
/// shared artifact cache on a warm run; the term and scope graph are folded on first use only.
#[derive(Debug)]
pub struct CodeFile {
    /// Repo-relative path.
    pub path: String,
    /// The walk's language guess.
    pub hint: LanguageHint,
    /// The adapter language tag, or [`OPAQUE`].
    pub language: String,
    /// The fidelity the file was folded at (F0 for an adapter-less file).
    pub fidelity: Fidelity,
    /// True when the file could not be read or folded: all of it is an unseen remainder.
    pub unreadable: bool,
    /// The text, kept only for a file that mentions `grimble:binds`.
    pub text: Option<String>,
    /// The symbol view; `None` for an unreadable file.
    symbols: Option<FileSymbols>,
    /// Whether the term holds an opaque region, a hole or an unexpanded phase.
    unseen: bool,
    /// The term and scope graph, folded on first use (set up front on a cache miss).
    folded: OnceLock<Option<Folded>>,
    /// Where to re-fold from: the source root and the walk entry.
    origin: (PathBuf, FileEntry),
    /// The artifact cache the folded term is read from and written back to.
    cache: CacheHandle,
}

/// A shared handle on the artifact cache (the cache itself has no `Debug`).
struct CacheHandle(Arc<Cache>);

impl std::fmt::Debug for CacheHandle {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("CacheHandle")
    }
}

/// How many files a [`Code::build`] folded from source versus read from the artifact cache.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct FoldStats {
    /// Files parsed and folded because no cache entry matched.
    pub folded: usize,
    /// Files whose symbol view and summary came from the cache (no parse).
    pub cached: usize,
}

/// One unit of a term: its symref text, node and unit kind.
#[derive(Clone, Debug)]
pub struct Unit {
    /// The symref spelled as text (the identity key).
    pub symref: String,
    /// The `unit` or `anon` node.
    pub node: NodeId,
    /// The unit kind (`module`, `function`, ...).
    pub kind: String,
}

impl CodeFile {
    /// True when the file is an adapter-less F0 opaque unit.
    pub fn is_opaque(&self) -> bool {
        self.language == OPAQUE
    }

    /// The source text re-read from disk (for textual receiver typing); `None` when unreadable.
    pub fn source(&self) -> Option<String> {
        let (root, entry) = &self.origin;
        match std::fs::read_to_string(root.join(&entry.path)) {
            Ok(t) => Some(t),
            Err(err) => {
                tracing::warn!(path = %self.path, %err, "source unreadable for receiver typing");
                None
            }
        }
    }

    /// The symbol view of the file; `None` when it is unreadable.
    pub fn symbols(&self) -> Option<&FileSymbols> {
        self.symbols.as_ref()
    }

    /// The term, scope graph and symbol view, folding the file now if the cache spared it so far.
    pub fn folded(&self) -> Option<&Folded> {
        self.folded
            .get_or_init(|| {
                if self.unreadable {
                    return None;
                }
                let (root, entry) = &self.origin;
                if let (Some(a), Some(symbols)) = (adapter_for(&entry.language), &self.symbols)
                    && let Some((term, scopes)) = cached_term(&self.cache.0, entry, a)
                {
                    tracing::debug!(path = %self.path, "term and scopes read from cache");
                    return Some(Folded {
                        term,
                        scopes,
                        file: symbols.clone(),
                    });
                }
                tracing::debug!(path = %self.path, "folding on demand (term not cached)");
                let text = if adapter_for(&entry.language).is_some() {
                    match std::fs::read_to_string(root.join(&entry.path)) {
                        Ok(t) => t,
                        Err(err) => {
                            tracing::warn!(path = %self.path, %err, "file unreadable on demand");
                            return None;
                        }
                    }
                } else {
                    String::new()
                };
                match counted_fold(entry, &text) {
                    Ok(f) => {
                        if let Some(a) = adapter_for(&entry.language)
                            && !f.file.degraded
                        {
                            store_term(&self.cache.0, entry, a, &f);
                        }
                        Some(f)
                    }
                    Err(err) => {
                        tracing::error!(path = %self.path, %err, "adapter bug: fold failed");
                        None
                    }
                }
            })
            .as_ref()
    }

    /// The units of the file in document order (empty when unreadable).
    pub fn units(&self) -> Vec<Unit> {
        let Some(f) = self.folded() else {
            return Vec::new();
        };
        f.term
            .units()
            .into_iter()
            .map(|u| Unit {
                symref: u.symref.to_string(),
                node: u.node,
                kind: unit_kind(&f.term, u.node),
            })
            .collect()
    }

    /// True when the term holds an opaque region, a hole or an unexpanded phase.
    pub fn has_unseen(&self) -> bool {
        self.unreadable || self.unseen
    }
}

/// True when `t` holds an opaque region, a hole or an unexpanded phase.
fn term_has_unseen(t: &Term) -> bool {
    t.ids().any(|id| match t.operator(id) {
        op if op.is_opaque() || op.is_hole() => true,
        Operator::Universal(Universal::Phase { .. }) => t.children(id).len() < 2,
        _ => false,
    })
}

/// The unit kind of `node` (`anon` units answer their anon kind).
pub fn unit_kind(term: &Term, node: NodeId) -> String {
    match term.operator(node) {
        Operator::Universal(Universal::Unit { kind, .. } | Universal::Anon { kind }) => {
            kind.clone()
        }
        _ => String::new(),
    }
}

/// Every walked file, folded, plus the walk as `gob-walk` selectors want it.
#[derive(Debug, Default)]
pub struct Code {
    /// Files sorted by path.
    pub files: Vec<CodeFile>,
    /// The walk (sorted, nothing oversized: the check core drops those).
    pub walk: WalkResult,
    /// Cache hits and misses of the build.
    pub stats: FoldStats,
    by_path: BTreeMap<String, usize>,
}

impl Code {
    /// Fold every entry of `entries` under `root` (in parallel), using the repository-shared cache.
    pub fn build(root: &Path, entries: &[FileEntry]) -> Self {
        Self::build_with(
            root,
            entries,
            &Arc::new(Cache::open_shared(root, STATE_DIR)),
        )
    }

    /// Like [`Code::build`] with an explicit artifact `cache`.
    pub fn build_with(root: &Path, entries: &[FileEntry], cache: &Arc<Cache>) -> Self {
        let cached = AtomicUsize::new(0);
        let mut files: Vec<CodeFile> = entries
            .par_iter()
            .map(|e| fold_entry(root, e, cache, &cached))
            .collect();
        files.sort_by(|a, b| a.path.cmp(&b.path));
        let mut sorted: Vec<FileEntry> = entries.to_vec();
        sorted.sort_by(|a, b| a.path.cmp(&b.path));
        let by_path = files
            .iter()
            .enumerate()
            .map(|(i, f)| (f.path.clone(), i))
            .collect();
        let cached = cached.into_inner();
        let stats = FoldStats {
            folded: files.len() - cached,
            cached,
        };
        tracing::info!(files = files.len(), cached, "code folded for binding");
        Self {
            files,
            walk: WalkResult {
                files: sorted,
                oversized: Vec::new(),
            },
            stats,
            by_path,
        }
    }

    /// Folds the terms of `paths` now, in parallel, so later serial readers find them ready.
    pub fn prefold(&self, paths: impl IntoIterator<Item = impl AsRef<str>>) {
        let files: Vec<&CodeFile> = paths
            .into_iter()
            .filter_map(|p| self.file(p.as_ref()))
            .collect();
        tracing::debug!(files = files.len(), "prefolding terms in parallel");
        files.par_iter().for_each(|f| {
            f.folded();
        });
    }

    /// The file at `path`.
    pub fn file(&self, path: &str) -> Option<&CodeFile> {
        self.by_path.get(path).map(|&i| &self.files[i])
    }
}

/// The cached per-file facts that spare a parse: `[unseen, mentions grimble:binds]`.
fn summary_key(e: &FileEntry, identity: &str) -> ArtifactKey {
    ArtifactKey {
        content_digest: e.digest.to_string(),
        producer_identity: format!("grimble-bind/summary-v1/{identity}"),
    }
}

/// The symbol view and summary of `e` from the cache, when both are present and match.
fn cached_facts(
    cache: &Cache,
    e: &FileEntry,
    adapter: &dyn Adapter,
) -> Option<(FileSymbols, bool, bool)> {
    let identity = adapter.identity();
    let sym = cache.get_artifact(&ArtifactKey {
        content_digest: e.digest.to_string(),
        producer_identity: identity.clone(),
    })?;
    let fs: FileSymbols = postcard_decode(&sym)?;
    if fs.path != e.path {
        return None;
    }
    let sum = cache.get_artifact(&summary_key(e, &identity))?;
    match sum.as_slice() {
        [unseen, binds] => Some((fs, *unseen != 0, *binds != 0)),
        _ => None,
    }
}

/// The cache key of the folded term and scope graph (schema version rides in the identity).
fn term_key(e: &FileEntry, adapter: &dyn Adapter) -> ArtifactKey {
    ArtifactKey {
        content_digest: e.digest.to_string(),
        producer_identity: format!(
            "grimble-bind/term-v{}/{}",
            gob_ir::TERM_SCHEMA_VERSION,
            adapter.identity()
        ),
    }
}

/// The cached term and scope graph of `e`; `None` on a miss, a corrupt entry or a mismatched pair.
fn cached_term(cache: &Cache, e: &FileEntry, adapter: &dyn Adapter) -> Option<(Term, ScopeGraph)> {
    let bytes = cache.get_artifact(&term_key(e, adapter))?;
    let (term, scopes): (Term, ScopeGraph) = match postcard::from_bytes(&bytes) {
        Ok(pair) => pair,
        Err(err) => {
            tracing::warn!(path = %e.path, %err, "cached term undecodable; refolding");
            return None;
        }
    };
    if !scopes.nodes_within(term.len()) {
        tracing::warn!(path = %e.path, "cached scope graph does not fit its term; refolding");
        return None;
    }
    Some((term, scopes))
}

/// Writes the folded term and scope graph to `cache`, best-effort.
fn store_term(cache: &Cache, e: &FileEntry, adapter: &dyn Adapter, folded: &Folded) {
    match postcard::to_stdvec(&(&folded.term, &folded.scopes)) {
        Ok(bytes) => cache.put_artifact(&term_key(e, adapter), &bytes),
        Err(err) => tracing::warn!(path = %e.path, %err, "term not serializable; not cached"),
    }
}

/// Decodes a cached payload; `None` (and a warning) when it is undecodable.
fn postcard_decode(bytes: &[u8]) -> Option<FileSymbols> {
    match postcard::from_bytes(bytes) {
        Ok(fs) => Some(fs),
        Err(err) => {
            tracing::warn!(%err, "cached symbol view undecodable; refolding");
            None
        }
    }
}

/// Encodes the symbol view exactly as frob's graph build does, so the entries are shared.
fn postcard_encode(fs: &FileSymbols) -> Option<Vec<u8>> {
    postcard::to_stdvec(fs).ok()
}

fn fold_entry(root: &Path, e: &FileEntry, cache: &Arc<Cache>, cached: &AtomicUsize) -> CodeFile {
    let adapter = adapter_for(&e.language);
    let language = adapter.map_or(OPAQUE, |a| a.language()).to_owned();
    if let Some(a) = adapter
        && let Some((fs, unseen, binds)) = cached_facts(cache.as_ref(), e, a)
    {
        let text = if binds {
            match std::fs::read_to_string(root.join(&e.path)) {
                Ok(t) => Some(t),
                Err(err) => {
                    tracing::warn!(path = %e.path, %err, "file unreadable; all of it is unseen");
                    return unreadable(root, e, language, cache);
                }
            }
        } else {
            None
        };
        cached.fetch_add(1, Ordering::Relaxed);
        return CodeFile {
            path: e.path.clone(),
            hint: e.language.clone(),
            language,
            fidelity: fs.fidelity,
            unreadable: false,
            text,
            symbols: Some(fs),
            unseen,
            folded: OnceLock::new(),
            origin: (root.to_path_buf(), e.clone()),
            cache: CacheHandle(Arc::clone(cache)),
        };
    }
    let text = if adapter.is_some() {
        match std::fs::read_to_string(root.join(&e.path)) {
            Ok(t) => Some(t),
            Err(err) => {
                tracing::warn!(path = %e.path, %err, "file unreadable; all of it is unseen");
                return unreadable(root, e, language, cache);
            }
        }
    } else {
        None
    };
    match counted_fold(e, text.as_deref().unwrap_or("")) {
        Ok(folded) => {
            let unseen = term_has_unseen(&folded.term);
            let binds = text.as_deref().is_some_and(|t| t.contains("grimble:binds"));
            if let Some(a) = adapter
                && !folded.file.degraded
            {
                store_facts(cache, e, a, &folded.file, unseen, binds);
                store_term(cache, e, a, &folded);
            }
            CodeFile {
                path: e.path.clone(),
                hint: e.language.clone(),
                language,
                fidelity: folded.file.fidelity,
                unreadable: false,
                text: text.filter(|_| binds),
                symbols: Some(folded.file.clone()),
                unseen,
                folded: OnceLock::from(Some(folded)),
                origin: (root.to_path_buf(), e.clone()),
                cache: CacheHandle(Arc::clone(cache)),
            }
        }
        Err(err) => {
            tracing::error!(path = %e.path, %err, "adapter bug: fold failed");
            unreadable(root, e, language, cache)
        }
    }
}

/// Writes the symbol view (the key frob's graph build also reads) and the summary to `cache`.
fn store_facts(
    cache: &Cache,
    e: &FileEntry,
    adapter: &dyn Adapter,
    fs: &FileSymbols,
    unseen: bool,
    binds: bool,
) {
    let identity = adapter.identity();
    let Some(bytes) = postcard_encode(fs) else {
        tracing::warn!(path = %e.path, "symbol view not serializable; not cached");
        return;
    };
    cache.put_artifact(
        &ArtifactKey {
            content_digest: e.digest.to_string(),
            producer_identity: identity.clone(),
        },
        &bytes,
    );
    cache.put_artifact(
        &summary_key(e, &identity),
        &[u8::from(unseen), u8::from(binds)],
    );
}

fn unreadable(root: &Path, e: &FileEntry, language: String, cache: &Arc<Cache>) -> CodeFile {
    CodeFile {
        path: e.path.clone(),
        hint: e.language.clone(),
        language,
        fidelity: Fidelity::F0,
        unreadable: true,
        text: None,
        symbols: None,
        unseen: true,
        folded: OnceLock::from(None),
        origin: (root.to_path_buf(), e.clone()),
        cache: CacheHandle(Arc::clone(cache)),
    }
}
