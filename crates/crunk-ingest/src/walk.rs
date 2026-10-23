//! The `css_root` walk, bucket placement and the ungoverned scan (the Python `ingest.walk`,
//! CSS part).
//!
//! Parsed contents are cached in `gob-cache` by content digest, so an unchanged tree is read
//! from the cache on the second run and gives the same result.

// frob:ticket 01M43ARY91XZ35DN9SCHRHS033

use std::collections::BTreeSet;
use std::path::{Component, Path, PathBuf};

use crunk_spec::DesignSpec;
use gob_cache::{ArtifactKey, Cache};
use gob_symbols::{Adapter, is_css_path};
use gob_walk::{Digest, FileEntry, LanguageHint, WalkConfig, walk_paths};
use rayon::prelude::*;

use crate::error::IngestError;
use crate::glob::glob_match;
use crate::model::{Bucket, ParseDiagnostic, ProjectStyles, Stylesheet};
use crate::parse::{ParsedCss, parse_css_source};

/// Bump when the parsed output changes for the same input; part of the cache key.
pub const INGEST_VERSION: u32 = 1;

/// Directories the ungoverned scan never enters, whatever `[org] ignore` says.
///
/// Generated report directories (`coverage`, `htmlcov`, ...) are not listed: the walk skips
/// them through the shared `gob_walk::GENERATED_DIRS` list.
// frob:ticket 01M5MDT81QR8F0E67N61AYZDN2
const NOISE_DIRS: [&str; 8] = [
    "node_modules",
    "venv",
    "dist",
    "build",
    "out",
    "vendor",
    "target",
    "__pycache__",
];

/// What one ingest did, for the report and the cache tests.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct IngestStats {
    /// Stylesheets that went through ingest.
    pub files: usize,
    /// Files parsed from source.
    pub parsed: usize,
    /// Files whose parse came from the cache.
    pub cached: usize,
    /// Named files skipped because they sit outside `css_root`.
    pub outside_css_root: usize,
    /// JSX and TS sources read from `[jsx] globs`.
    pub jsx_files: usize,
    /// JSX and TS sources whose facts were computed this run.
    pub jsx_parsed: usize,
    /// JSX and TS sources whose facts came from the cache.
    pub jsx_cached: usize,
}

/// The result of an ingest: the styles and what it cost.
#[derive(Debug, Clone, PartialEq)]
pub struct Ingested {
    /// The ingested project styles.
    pub styles: ProjectStyles,
    /// Counts of parsed, cached and skipped files.
    pub stats: IngestStats,
}

/// Classify the file at `relative` (to `css_root`, POSIX separators) per the org rules.
///
/// Checked in order: the tokens file, an `[org] entry` glob (entry sheets are exempt from
/// bucket placement wherever they sit), then the first path segment against `[org] buckets`.
pub fn bucket_for(
    relative: &Path,
    is_tokens_file: bool,
    spec: &DesignSpec,
) -> (Option<Bucket>, Option<String>) {
    if is_tokens_file {
        return (Some(Bucket::Tokens), None);
    }
    let posix = posix(relative);
    if spec.org.entry.iter().any(|p| glob_match(&posix, p)) {
        return (Some(Bucket::Entry), None);
    }
    let first = relative
        .components()
        .next()
        .map(|c| c.as_os_str().to_string_lossy().into_owned())
        .unwrap_or_default();
    if spec.org.buckets.contains(&first)
        && let Some(bucket) = Bucket::from_name(&first)
    {
        let component = (bucket == Bucket::Components)
            .then(|| {
                relative
                    .file_stem()
                    .map(|s| s.to_string_lossy().into_owned())
            })
            .flatten();
        return (Some(bucket), component);
    }
    (None, None)
}

pub(crate) fn posix(path: &Path) -> String {
    path.components()
        .map(|c| c.as_os_str().to_string_lossy())
        .collect::<Vec<_>>()
        .join("/")
}

fn component_key(path: &Path) -> Vec<Component<'_>> {
    path.components().collect()
}

/// `path` resolved against the file system, or as given when it does not exist (yet).
fn canonical(path: &Path) -> PathBuf {
    gob_exec::canonical(path).unwrap_or_else(|_| path.to_path_buf())
}

fn producer_identity(root_font_size: f64) -> String {
    format!(
        "crunk-ingest/v{INGEST_VERSION}/{}/rfs={root_font_size}",
        gob_symbols::CssAdapter.identity()
    )
}

/// What loading one file produced, before it is placed.
enum Loaded {
    /// The file sits outside `css_root`.
    Outside,
    /// Unreadable, not UTF-8 or unparsable; the message becomes a diagnostic.
    Failed(String),
    /// Parsed or loaded from the cache.
    Parsed(Box<LoadedSheet>),
}

struct LoadedSheet {
    canon: PathBuf,
    relative: PathBuf,
    source: String,
    parsed: ParsedCss,
    was_cached: bool,
}

struct Ingest<'a> {
    spec: &'a DesignSpec,
    cache: &'a Cache,
    css_root: PathBuf,
    tokens_path: PathBuf,
    identity: String,
    styles: ProjectStyles,
    stats: IngestStats,
}

impl<'a> Ingest<'a> {
    fn new(spec: &'a DesignSpec, cache: &'a Cache) -> Self {
        let css_root = canonical(&spec.css_root());
        let tokens_path = {
            let t = spec.tokens_path();
            gob_exec::canonical(&t).unwrap_or_else(|_| {
                // The tokens file may not exist yet; resolve its directory instead.
                t.parent()
                    .map(canonical)
                    .zip(t.file_name())
                    .map_or_else(|| t.clone(), |(d, f)| d.join(f))
            })
        };
        Self {
            spec,
            cache,
            css_root,
            tokens_path,
            identity: producer_identity(spec.project.root_font_size),
            styles: ProjectStyles::default(),
            stats: IngestStats::default(),
        }
    }

    fn diagnostic(&mut self, path: &Path, message: impl Into<String>) {
        let message = message.into();
        tracing::info!(path = %path.display(), %message, "ingest: diagnostic");
        self.styles.diagnostics.push(ParseDiagnostic {
            path: path.to_path_buf(),
            message,
        });
    }

    /// Read and parse (or load from the cache) one file; touches no shared state.
    ///
    /// frob:ticket 01M4DPJR7RFS40YTGVT80A3EXX
    fn load(&self, path: &Path) -> Loaded {
        let canon = canonical(path);
        let Ok(relative) = canon.strip_prefix(&self.css_root) else {
            return Loaded::Outside;
        };
        let relative = relative.to_path_buf();
        let bytes = match std::fs::read(path) {
            Ok(b) => b,
            Err(err) => return Loaded::Failed(err.to_string()),
        };
        let source = match String::from_utf8(bytes) {
            Ok(s) => s,
            Err(err) => return Loaded::Failed(err.to_string()),
        };
        // Hash the bytes as read, not the walk's git-filtered digest: spans are byte offsets
        // into this exact text, so a CRLF checkout must not share a cache entry with its LF twin.
        let digest = Digest::of(source.as_bytes());
        let entry = FileEntry {
            path: posix(&relative),
            size: source.len() as u64,
            digest,
            language: LanguageHint::from_path("x.css"),
        };
        let key = ArtifactKey {
            content_digest: digest.to_string(),
            producer_identity: self.identity.clone(),
        };
        let cached = self
            .cache
            .get_artifact(&key)
            .and_then(|b| serde_json::from_slice::<ParsedCss>(&b).ok());
        let (parsed, was_cached) = if let Some(hit) = cached {
            tracing::debug!(path = %path.display(), "ingest: parse cache hit");
            (hit, true)
        } else {
            match parse_css_source(&entry, &source, self.spec.project.root_font_size) {
                Ok(p) => {
                    if let Ok(bytes) = serde_json::to_vec(&p) {
                        self.cache.put_artifact(&key, &bytes);
                    }
                    (p, false)
                }
                Err(err) => return Loaded::Failed(err.to_string()),
            }
        };
        Loaded::Parsed(Box::new(LoadedSheet {
            canon,
            relative,
            source,
            parsed,
            was_cached,
        }))
    }

    /// Parse `paths` in parallel, then place the results in input order.
    ///
    /// frob:ticket 01M4DPJR7RFS40YTGVT80A3EXX
    fn files(&mut self, paths: &[PathBuf]) {
        let loaded: Vec<Loaded> = paths.par_iter().map(|p| self.load(p)).collect();
        for (path, loaded) in paths.iter().zip(loaded) {
            self.place(path, loaded);
        }
    }

    /// Record one loaded file's sheet, stray and diagnostic.
    fn place(&mut self, path: &Path, loaded: Loaded) {
        let sheet = match loaded {
            Loaded::Outside => {
                self.stats.outside_css_root += 1;
                tracing::info!(path = %path.display(), "ingest: file outside css_root skipped");
                return;
            }
            Loaded::Failed(message) => {
                self.diagnostic(path, message);
                return;
            }
            Loaded::Parsed(sheet) => *sheet,
        };
        let LoadedSheet {
            canon,
            relative,
            source,
            parsed,
            was_cached,
        } = sheet;
        if was_cached {
            self.stats.cached += 1;
        } else {
            self.stats.parsed += 1;
        }
        self.stats.files += 1;
        let (bucket, component) = bucket_for(&relative, canon == self.tokens_path, self.spec);
        if !parsed.errors.is_empty() {
            self.diagnostic(path, parsed.errors.join("; "));
        }
        if bucket.is_none() {
            self.styles.strays.push(path.to_path_buf());
        }
        tracing::debug!(
            path = %path.display(),
            bucket = bucket.map(Bucket::as_str),
            decls = parsed.declarations.len(),
            "ingest: sheet placed"
        );
        self.styles.sheets.push(Stylesheet {
            path: path.to_path_buf(),
            bucket,
            component,
            source,
            declarations: parsed.declarations,
            class_selectors: parsed.class_selectors,
            custom_props: parsed.custom_props,
            orphan_waivers: parsed.orphan_waivers,
            media_queries: parsed.media_queries,
            utilities: Vec::new(),
            dynamic_classes: Vec::new(),
        });
    }

    /// Add the JSX and TS sources of `[jsx] globs` (or the named ones) after the CSS sheets.
    fn jsx(&mut self, only: Option<&[PathBuf]>) -> Result<(), IngestError> {
        let jsx = crate::jsx::ingest(self.spec, self.cache, only)?;
        self.stats.jsx_files = jsx.files;
        self.stats.jsx_parsed = jsx.parsed;
        self.stats.jsx_cached = jsx.cached;
        self.styles.sheets.extend(jsx.sheets);
        self.styles.diagnostics.extend(jsx.diagnostics);
        Ok(())
    }

    fn finish(self) -> Ingested {
        tracing::info!(
            sheets = self.styles.sheets.len(),
            strays = self.styles.strays.len(),
            diagnostics = self.styles.diagnostics.len(),
            ungoverned = self.styles.ungoverned.len(),
            parsed = self.stats.parsed,
            cached = self.stats.cached,
            "ingest complete"
        );
        Ingested {
            styles: self.styles,
            stats: self.stats,
        }
    }
}

/// The `.css` files under `dir` (ignore files honored) as absolute paths, in component order.
fn css_files_under(dir: &Path) -> Result<Vec<PathBuf>, IngestError> {
    // frob:ticket 01M4DPJR7RFS40YTGVT80A3EXX
    let walked = walk_paths(dir, &WalkConfig::default()).map_err(|source| IngestError::Walk {
        path: dir.to_path_buf(),
        source,
    })?;
    let mut files: Vec<PathBuf> = walked
        .files
        .into_iter()
        .filter(|f| is_css_path(&f.path))
        .map(|f| dir.join(&f.path))
        .collect();
    files.sort_by(|a, b| component_key(a).cmp(&component_key(b)));
    Ok(files)
}

/// `.css` files under the project root outside `css_root` that no `[org] ignore` glob covers.
fn find_ungoverned(spec: &DesignSpec, css_root: &Path) -> Result<Vec<PathBuf>, IngestError> {
    let root = spec.root.as_path();
    if !root.is_dir() {
        return Ok(Vec::new());
    }
    let mut exclude: Vec<String> = NOISE_DIRS.iter().map(|d| format!("{d}/")).collect();
    exclude.push(".*/".to_owned());
    // frob:ticket 01M4DPJR7RFS40YTGVT80A3EXX
    // Path-only: nothing here needs a digest, so no file is read.
    let walked = walk_paths(
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
    let css_root = canonical(css_root);
    let mut found: Vec<PathBuf> = walked
        .files
        .into_iter()
        .filter(|f| is_css_path(&f.path))
        .filter(|f| !canonical(&root.join(&f.path)).starts_with(&css_root))
        .filter(|f| {
            let ignored = spec.org.ignore.iter().any(|p| glob_match(&f.path, p));
            if ignored {
                tracing::debug!(path = %f.path, "ingest: ungoverned file ignored");
            }
            !ignored
        })
        .map(|f| root.join(&f.path))
        .collect();
    found.sort_by(|a, b| component_key(a).cmp(&component_key(b)));
    tracing::info!(found = found.len(), "ingest: ungoverned scan complete");
    Ok(found)
}

/// Walk `css_root`, parse every `.css` file and place it in a bucket.
///
/// An absent css root is a diagnostic, not an error (JSX and Tailwind sources may still
/// apply); a css root that exists but is not a directory is an error.
///
/// # Errors
///
/// [`IngestError::CssRootNotDirectory`] when `css_root` is not a directory;
/// [`IngestError::Walk`] when a directory walk cannot start.
pub fn ingest_tree(spec: &DesignSpec, cache: &Cache) -> Result<Ingested, IngestError> {
    let mut ingest = Ingest::new(spec, cache);
    let css_root = spec.css_root();
    let files = if css_root.exists() {
        if !css_root.is_dir() {
            return Err(IngestError::CssRootNotDirectory(css_root));
        }
        css_files_under(&css_root)?
    } else {
        ingest.diagnostic(
            &css_root,
            format!(
                "css root {} does not exist; CSS judgments skipped, jsx/tailwind sources still ingest",
                css_root.display()
            ),
        );
        Vec::new()
    };
    ingest.styles.ungoverned = find_ungoverned(spec, &css_root)?;
    ingest.files(&files);
    ingest.jsx(None)?;
    Ok(ingest.finish())
}

/// Like [`ingest_tree`], restricted to the named files and directories (CLI PATH arguments).
///
/// A named file outside `css_root` (a git-ignored build output, say) is skipped and counted in
/// [`IngestStats::outside_css_root`], never a crash. The ungoverned scan stays empty: it is
/// project-scope only. Relative paths resolve against the process working directory.
///
/// # Errors
///
/// [`IngestError::Walk`] when a named directory cannot be walked.
pub fn ingest_paths(
    paths: &[PathBuf],
    spec: &DesignSpec,
    cache: &Cache,
) -> Result<Ingested, IngestError> {
    let mut ingest = Ingest::new(spec, cache);
    let mut seen: BTreeSet<PathBuf> = BTreeSet::new();
    let mut named: Vec<PathBuf> = Vec::new();
    for p in paths {
        if p.is_dir() {
            for file in css_files_under(p)? {
                if seen.insert(file.clone()) {
                    named.push(file);
                }
            }
        } else if is_css_path(&p.to_string_lossy()) && seen.insert(p.clone()) {
            named.push(p.clone());
        }
    }
    named.sort_by(|a, b| component_key(a).cmp(&component_key(b)));
    ingest.files(&named);
    ingest.jsx(Some(paths))?;
    Ok(ingest.finish())
}
