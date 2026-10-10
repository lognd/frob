//! The code side of binding: every walked file folded into a U term and scope graph.

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC
// frob:ticket 01M4D6NGJANPW3T3DKM77B0T1W
// frob:ticket 01M4HW9Y1TXZCN4Y5RF2T7C4A9

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::OnceLock;
use std::sync::atomic::{AtomicUsize, Ordering};

use gob_cache::{ArtifactKey, Cache};
use gob_ir::{NodeId, Operator, Term, Universal};
use gob_symbols::{Adapter, Fidelity, FileSymbols, Folded, adapter_for};

use crate::frob_owned::STATE_DIR;
use gob_walk::{FileEntry, LanguageHint, WalkResult};
use rayon::prelude::*;

/// The tag of a file no adapter claims.
pub const OPAQUE: &str = "opaque";

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
                tracing::debug!(path = %self.path, "folding on demand (term not cached)");
                let (root, entry) = &self.origin;
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
                match gob_symbols::fold_file(entry, &text) {
                    Ok(f) => Some(f),
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
        Self::build_with(root, entries, &Cache::open_shared(root, STATE_DIR))
    }

    /// Like [`Code::build`] with an explicit artifact `cache`.
    pub fn build_with(root: &Path, entries: &[FileEntry], cache: &Cache) -> Self {
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

fn fold_entry(root: &Path, e: &FileEntry, cache: &Cache, cached: &AtomicUsize) -> CodeFile {
    let adapter = adapter_for(&e.language);
    let language = adapter.map_or(OPAQUE, |a| a.language()).to_owned();
    if let Some(a) = adapter
        && let Some((fs, unseen, binds)) = cached_facts(cache, e, a)
    {
        let text = if binds {
            match std::fs::read_to_string(root.join(&e.path)) {
                Ok(t) => Some(t),
                Err(err) => {
                    tracing::warn!(path = %e.path, %err, "file unreadable; all of it is unseen");
                    return unreadable(root, e, language);
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
        };
    }
    let text = if adapter.is_some() {
        match std::fs::read_to_string(root.join(&e.path)) {
            Ok(t) => Some(t),
            Err(err) => {
                tracing::warn!(path = %e.path, %err, "file unreadable; all of it is unseen");
                return unreadable(root, e, language);
            }
        }
    } else {
        None
    };
    match gob_symbols::fold_file(e, text.as_deref().unwrap_or("")) {
        Ok(folded) => {
            let unseen = term_has_unseen(&folded.term);
            let binds = text.as_deref().is_some_and(|t| t.contains("grimble:binds"));
            if let Some(a) = adapter
                && !folded.file.degraded
            {
                store_facts(cache, e, a, &folded.file, unseen, binds);
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
            }
        }
        Err(err) => {
            tracing::error!(path = %e.path, %err, "adapter bug: fold failed");
            unreadable(root, e, language)
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

fn unreadable(root: &Path, e: &FileEntry, language: String) -> CodeFile {
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
    }
}
