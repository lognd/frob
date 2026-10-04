//! Per-file extraction and the parallel, cached graph build.

// frob:ticket 01M3Z713F6VY15YSMS15033RN1

use std::path::Path;
use std::sync::atomic::{AtomicUsize, Ordering};

use gob_cache::{ArtifactKey, Cache};
use gob_languages::ParseLimits;
use gob_walk::{ContentSource, FileEntry};
use rayon::prelude::*;

use crate::adapter::{Adapter, Fidelity, FileInput, Folded, ParseStatus};
use crate::crates::CrateDeps;
use crate::fold::{base_file, opaque_file};
use crate::graph::SymbolGraph;
use crate::model::FileSymbols;
use crate::registry::adapter_for;

/// Bump when extraction output changes for the same input; part of the
/// cache key.
pub const EXTRACTOR_VERSION: u32 = 14;

/// Files read per filter pipeline (building one loads the index and attributes).
const READ_CHUNK: usize = 256;

/// Counters from one [`build_graph_with_stats`] run.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct BuildStats {
    /// Files extracted from source (cache misses).
    pub extracted: usize,
    /// Files served from the cache.
    pub cached: usize,
    /// Files that could not be read.
    pub skipped: usize,
    /// Files no adapter claims, folded as one opaque unit each (G19).
    pub opaque: usize,
}

fn input_of<'a>(entry: &'a FileEntry, digest: &'a str, text_len: usize) -> FileInput<'a> {
    FileInput {
        path: &entry.path,
        digest,
        size: u32::try_from(text_len).unwrap_or(u32::MAX),
    }
}

/// Folds one file's `text` into its term, scope graph and compatibility view.
///
/// Adapter-less files fold to one opaque unit at F0; `text` is not read for them.
///
/// # Errors
///
/// [`crate::FoldError`] only when an adapter builds an ill-formed term (a bug).
pub fn fold_file(entry: &FileEntry, text: &str) -> Result<Folded, crate::FoldError> {
    let digest = entry.digest.to_string();
    let Some(adapter) = adapter_for(&entry.language) else {
        let size = u32::try_from(entry.size).unwrap_or(u32::MAX);
        let input = FileInput {
            path: &entry.path,
            digest: &digest,
            size,
        };
        tracing::debug!(path = %entry.path, "no adapter for language");
        return opaque_fold(&input);
    };
    let input = input_of(entry, &digest, text.len());
    let tree = adapter.parse(text, &ParseLimits::default());
    adapter.fold(&tree, &input)
}

fn opaque_fold(input: &FileInput<'_>) -> Result<Folded, crate::FoldError> {
    let ext = Path::new(input.path)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    opaque_file(input, &ext)
}

/// Extracts symbols, imports, call sites and references from one file's `text`.
///
/// A file whose language has no adapter yields one opaque unit at F0
/// (`parse_status` is `NotParsed`); an unparsable file yields no symbols with
/// `degraded` set and `parse_status` `Failed`.
pub fn extract_file(entry: &FileEntry, text: &str) -> FileSymbols {
    match fold_file(entry, text) {
        Ok(f) => f.file,
        Err(err) => {
            tracing::error!(path = %entry.path, %err, "adapter bug: fold failed");
            let digest = entry.digest.to_string();
            let mut out = base_file(&input_of(entry, &digest, text.len()), "");
            out.degraded = true;
            out.fidelity = Fidelity::F0;
            out.parse_status = ParseStatus::Failed {
                reason: err.to_string(),
            };
            out
        }
    }
}

fn key(entry: &FileEntry, adapter: &dyn Adapter) -> ArtifactKey {
    ArtifactKey {
        content_digest: entry.digest.to_string(),
        producer_identity: adapter.identity(),
    }
}

/// Builds the repository symbol graph for `files` under `root`.
pub fn build_graph(root: &Path, files: &[FileEntry], cache: &Cache) -> SymbolGraph {
    build_graph_with_stats(root, files, cache).0
}

// frob:ticket 01M41ZSWGC86TY3K0NSA8AMNGF
/// Like [`build_graph`], also returning hit/miss counters.
///
/// Per-file artifacts are the serialized [`FileSymbols`] view, keyed by file
/// digest and the adapter identity (name, version, grammar identity). The U term
/// itself is not cached: gob-ir has no serialization yet, so a miss re-folds the
/// file from source.
pub fn build_graph_with_stats(
    root: &Path,
    files: &[FileEntry],
    cache: &Cache,
) -> (SymbolGraph, BuildStats) {
    let started = std::time::Instant::now();
    let extracted = AtomicUsize::new(0);
    let cached = AtomicUsize::new(0);
    let skipped = AtomicUsize::new(0);
    let opaque = AtomicUsize::new(0);
    // Text is read as git would store it, matching the walk's digests (CRLF checkouts parse as LF).
    let source = ContentSource::locate(root);
    let per_file: Vec<FileSymbols> = files
        .par_chunks(READ_CHUNK)
        .flat_map_iter(|chunk| {
            source.with_reader(|reader| {
                chunk
                    .iter()
                    .filter_map(|entry| {
            let Some(adapter) = adapter_for(&entry.language) else {
                opaque.fetch_add(1, Ordering::Relaxed);
                return Some(extract_file(entry, ""));
            };
            let k = key(entry, adapter);
            if let Some(bytes) = cache.get_artifact(&k) {
                match postcard::from_bytes::<FileSymbols>(&bytes) {
                    Ok(fs) if fs.path == entry.path => {
                        cached.fetch_add(1, Ordering::Relaxed);
                        return Some(fs);
                    }
                    Ok(_) => {
                        tracing::debug!(path = %entry.path, "cached payload is for another path");
                    }
                    Err(err) => {
                        tracing::warn!(path = %entry.path, %err, "cached payload undecodable");
                    }
                }
            }
            let text = match reader.read_text(&entry.path) {
                Ok(t) => t,
                Err(err) => {
                    tracing::warn!(path = %entry.path, %err, "unreadable file skipped");
                    skipped.fetch_add(1, Ordering::Relaxed);
                    return None;
                }
            };
            let fs = extract_file(entry, &text);
            extracted.fetch_add(1, Ordering::Relaxed);
            if fs.degraded {
                return Some(fs);
            }
            match postcard::to_stdvec(&fs) {
                Ok(bytes) => cache.put_artifact(&k, &bytes),
                Err(err) => tracing::warn!(path = %entry.path, %err, "payload not serializable"),
            }
            Some(fs)
                    })
                    .collect::<Vec<_>>()
            })
        })
        .collect();
    let stats = BuildStats {
        extracted: extracted.load(Ordering::Relaxed),
        cached: cached.load(Ordering::Relaxed),
        skipped: skipped.load(Ordering::Relaxed),
        opaque: opaque.load(Ordering::Relaxed),
    };
    let per_file_ms = started.elapsed().as_millis();
    tracing::info!(?stats, per_file_ms, "symbol extraction done");
    let graph = SymbolGraph::from_files_with_deps(per_file, &mut CrateDeps::new(root));
    tracing::info!(
        assemble_ms = started.elapsed().as_millis() - per_file_ms,
        "symbol graph assembled"
    );
    (graph, stats)
}
