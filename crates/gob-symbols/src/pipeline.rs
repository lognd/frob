//! Per-file extraction and the parallel, cached graph build.

use std::path::Path;
use std::sync::atomic::{AtomicUsize, Ordering};

use gob_cache::{ArtifactKey, Cache};
use gob_languages::{Language, ParseLimits, ParseResult, grammar_identity, parse};
use gob_walk::{FileEntry, LanguageHint};
use rayon::prelude::*;

use crate::graph::SymbolGraph;
use crate::model::FileSymbols;
use crate::{markdown, rust};

/// Bump when extraction output changes for the same input; part of the
/// cache key.
pub const EXTRACTOR_VERSION: u32 = 1;

/// Counters from one [`build_graph_with_stats`] run.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct BuildStats {
    /// Files extracted from source (cache misses).
    pub extracted: usize,
    /// Files served from the cache.
    pub cached: usize,
    /// Files with no supported language, unreadable or unparsable.
    pub skipped: usize,
}

fn language_of(entry: &FileEntry) -> Option<Language> {
    match entry.language {
        LanguageHint::Rust => Some(Language::Rust),
        LanguageHint::Markdown => Some(Language::Markdown),
        _ => None,
    }
}

/// Extracts symbols, imports and call sites from one file's `text`.
///
/// Files of other languages yield an empty result; an unparsable file yields
/// an empty result with `degraded` set.
pub fn extract_file(entry: &FileEntry, text: &str) -> FileSymbols {
    let out = FileSymbols {
        path: entry.path.clone(),
        file_digest: entry.digest.to_string(),
        size: u32::try_from(text.len()).unwrap_or(u32::MAX),
        ..FileSymbols::default()
    };
    let Some(lang) = language_of(entry) else {
        return out;
    };
    match parse(lang, text, &ParseLimits::default()) {
        ParseResult::Parsed(tree) => {
            if tree.has_errors() {
                tracing::warn!(path = %entry.path, "syntax errors; extracting what parsed");
            }
            match lang {
                Language::Rust => rust::extract(&tree, &entry.path, out),
                _ => markdown::extract(&tree, &entry.path, out),
            }
        }
        ParseResult::Unresolved(u) => {
            tracing::warn!(path = %entry.path, reason = %u.reason, "file not extracted");
            FileSymbols {
                degraded: true,
                ..out
            }
        }
    }
}

fn key(entry: &FileEntry, lang: Language) -> ArtifactKey {
    ArtifactKey {
        content_digest: entry.digest.to_string(),
        producer_identity: format!(
            "gob-symbols/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(lang)
        ),
    }
}

/// Builds the repository symbol graph for `files` under `root`.
pub fn build_graph(root: &Path, files: &[FileEntry], cache: &Cache) -> SymbolGraph {
    build_graph_with_stats(root, files, cache).0
}

/// Like [`build_graph`], also returning hit/miss counters.
pub fn build_graph_with_stats(
    root: &Path,
    files: &[FileEntry],
    cache: &Cache,
) -> (SymbolGraph, BuildStats) {
    let extracted = AtomicUsize::new(0);
    let cached = AtomicUsize::new(0);
    let skipped = AtomicUsize::new(0);
    let per_file: Vec<FileSymbols> = files
        .par_iter()
        .filter_map(|entry| {
            let Some(lang) = language_of(entry) else {
                skipped.fetch_add(1, Ordering::Relaxed);
                return None;
            };
            let k = key(entry, lang);
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
            let text = match std::fs::read_to_string(root.join(&entry.path)) {
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
        .collect();
    let stats = BuildStats {
        extracted: extracted.load(Ordering::Relaxed),
        cached: cached.load(Ordering::Relaxed),
        skipped: skipped.load(Ordering::Relaxed),
    };
    tracing::info!(?stats, "symbol extraction done");
    (SymbolGraph::from_files(per_file), stats)
}
