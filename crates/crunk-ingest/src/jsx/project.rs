//! The `[jsx] globs` walk: candidate files, the project's TS sources, one cached result.

// frob:ticket 01M43ARYFVG86PAGGM78JGRZY3

use std::path::{Path, PathBuf};

use crunk_spec::DesignSpec;
use gob_cache::{ArtifactKey, Cache};
use gob_symbols::{ConstProject, Folded, SymbolGraph, fold_file, is_typescript_path};
use gob_walk::{Digest, FileEntry, LanguageHint, WalkConfig, walk};
use serde::{Deserialize, Serialize};

use super::{ParsedJsx, parse_in_project};
use crate::error::IngestError;
use crate::glob::glob_match;
use crate::model::{Bucket, ParseDiagnostic, Stylesheet};

/// Bump when the parsed output changes for the same input; part of the cache key.
pub const JSX_INGEST_VERSION: u32 = 1;

/// Directories the walk never enters, whatever the ignore files say (as for ungoverned CSS).
const NOISE_DIRS: [&str; 9] = [
    "node_modules",
    "venv",
    "dist",
    "build",
    "out",
    "coverage",
    "vendor",
    "target",
    "__pycache__",
];

/// What the JSX part of an ingest produced.
#[derive(Debug, Default)]
pub(crate) struct JsxIngest {
    /// One sheet per candidate source, in path order.
    pub sheets: Vec<Stylesheet>,
    /// Unreadable files and syntax errors.
    pub diagnostics: Vec<ParseDiagnostic>,
    /// Candidate sources read.
    pub files: usize,
    /// Candidates whose facts were computed this run.
    pub parsed: usize,
    /// Candidates whose facts came from the cache.
    pub cached: usize,
}

/// The cached facts of every candidate of one source tree.
#[derive(Debug, Serialize, Deserialize)]
struct CachedTree {
    files: Vec<(String, ParsedJsx)>,
}

/// One TS-family source of the project, as read.
struct Source {
    /// Path relative to the project root, POSIX separators.
    relative: String,
    text: String,
    /// Digest of the bytes as read (spans are byte offsets into exactly this text).
    digest: Digest,
}

fn identity(root_font_size: f64) -> String {
    format!("crunk-ingest-jsx/v{JSX_INGEST_VERSION}/rfs={root_font_size}")
}

/// The project's TS-family sources, read from disk, in path order; unreadable ones become
/// diagnostics when they are candidates.
fn read_sources(
    spec: &DesignSpec,
    diagnostics: &mut Vec<ParseDiagnostic>,
    is_candidate: &dyn Fn(&str) -> bool,
) -> Result<Vec<Source>, IngestError> {
    let root = spec.root.as_path();
    let mut exclude: Vec<String> = NOISE_DIRS.iter().map(|d| format!("{d}/")).collect();
    exclude.push(".*/".to_owned());
    let walked = walk(
        root,
        &WalkConfig {
            exclude,
            ..WalkConfig::default()
        },
    )
    .map_err(|source| IngestError::Walk {
        path: root.to_path_buf(),
        source,
    })?;
    let mut sources = Vec::new();
    for file in walked
        .files
        .into_iter()
        .filter(|f| is_typescript_path(&f.path))
    {
        let path = root.join(&file.path);
        match std::fs::read(&path).map(String::from_utf8) {
            Ok(Ok(text)) => sources.push(Source {
                digest: Digest::of(text.as_bytes()),
                relative: file.path,
                text,
            }),
            Ok(Err(err)) => {
                if is_candidate(&file.path) {
                    diagnostics.push(diagnostic(&path, err.to_string()));
                }
            }
            Err(err) => {
                if is_candidate(&file.path) {
                    diagnostics.push(diagnostic(&path, err.to_string()));
                }
            }
        }
    }
    sources.sort_by(|a, b| a.relative.cmp(&b.relative));
    Ok(sources)
}

fn diagnostic(path: &Path, message: String) -> ParseDiagnostic {
    tracing::info!(path = %path.display(), %message, "jsx ingest: diagnostic");
    ParseDiagnostic {
        path: path.to_path_buf(),
        message,
    }
}

/// The digest of the whole TS source tree plus the settings that shape the output.
fn tree_key(sources: &[Source], root_font_size: f64) -> ArtifactKey {
    let mut bytes = Vec::new();
    for s in sources {
        bytes.extend_from_slice(s.relative.as_bytes());
        bytes.push(0);
        bytes.extend_from_slice(s.digest.to_string().as_bytes());
        bytes.push(0);
    }
    ArtifactKey {
        content_digest: Digest::of(&bytes).to_string(),
        producer_identity: identity(root_font_size),
    }
}

/// Fold every source and read the facts of the candidates.
fn parse_tree(sources: &[Source], candidates: &[&Source], root_font_size: f64) -> CachedTree {
    let mut folded: Vec<(&Source, Folded)> = Vec::new();
    for s in sources {
        let entry = FileEntry {
            path: s.relative.clone(),
            size: s.text.len() as u64,
            digest: s.digest,
            language: LanguageHint::from_path(&s.relative),
        };
        match fold_file(&entry, &s.text) {
            Ok(f) => folded.push((s, f)),
            Err(err) => tracing::error!(path = %s.relative, %err, "adapter bug: jsx fold failed"),
        }
    }
    let graph = SymbolGraph::from_files(folded.iter().map(|(_, f)| f.file.clone()).collect());
    let mut project = ConstProject::new(&graph);
    for (s, f) in &folded {
        project.add_file(&s.relative, f);
    }
    let files = candidates
        .iter()
        .filter(|c| folded.iter().any(|(s, _)| s.relative == c.relative))
        .map(|c| {
            (
                c.relative.clone(),
                parse_in_project(&c.relative, &c.text, root_font_size, &project),
            )
        })
        .collect();
    CachedTree { files }
}

/// Whether the named `paths` (files or directories) cover the candidate at `absolute`.
fn named(paths: &[PathBuf], absolute: &Path) -> bool {
    let canon = gob_exec::canonical(absolute).unwrap_or_else(|_| absolute.to_path_buf());
    paths.iter().any(|p| {
        let p = gob_exec::canonical(p).unwrap_or_else(|_| p.clone());
        canon == p || (p.is_dir() && canon.starts_with(&p))
    })
}

/// Ingest the `[jsx] globs` sources of the project (or, with `only`, the named ones).
///
/// Empty `globs` switches the feature off. An unchanged source tree reads the cache.
pub(crate) fn ingest(
    spec: &DesignSpec,
    cache: &Cache,
    only: Option<&[PathBuf]>,
) -> Result<JsxIngest, IngestError> {
    let globs = &spec.jsx.globs;
    let mut out = JsxIngest::default();
    if globs.is_empty() {
        return Ok(out);
    }
    let matches = |rel: &str| globs.iter().any(|g| glob_match(rel, g));
    let sources = read_sources(spec, &mut out.diagnostics, &matches)?;
    let candidates: Vec<&Source> = sources.iter().filter(|s| matches(&s.relative)).collect();
    if candidates.is_empty() {
        return Ok(out);
    }
    let key = tree_key(&sources, spec.project.root_font_size);
    let cached = cache
        .get_artifact(&key)
        .and_then(|b| serde_json::from_slice::<CachedTree>(&b).ok());
    let tree = if let Some(hit) = cached {
        out.cached = hit.files.len();
        tracing::debug!(files = hit.files.len(), "jsx ingest: cache hit");
        hit
    } else {
        let parsed = parse_tree(&sources, &candidates, spec.project.root_font_size);
        out.parsed = parsed.files.len();
        if let Ok(bytes) = serde_json::to_vec(&parsed) {
            cache.put_artifact(&key, &bytes);
        }
        parsed
    };
    for (relative, parsed) in tree.files {
        let path = spec.root.join(&relative);
        if only.is_some_and(|paths| !named(paths, &path)) {
            continue;
        }
        let Some(source) = candidates.iter().find(|c| c.relative == relative) else {
            continue;
        };
        if !parsed.errors.is_empty() {
            out.diagnostics
                .push(diagnostic(&path, parsed.errors.join("; ")));
        }
        out.files += 1;
        out.sheets.push(Stylesheet {
            component: path.file_stem().map(|s| s.to_string_lossy().into_owned()),
            path,
            bucket: Some(Bucket::Jsx),
            source: source.text.clone(),
            declarations: parsed.declarations,
            class_selectors: Vec::new(),
            custom_props: Vec::new(),
            orphan_waivers: Vec::new(),
            media_queries: Vec::new(),
            utilities: parsed.utilities,
            dynamic_classes: parsed.dynamic_classes,
        });
    }
    tracing::info!(
        sheets = out.sheets.len(),
        parsed = out.parsed,
        cached = out.cached,
        "jsx ingest complete"
    );
    Ok(out)
}
