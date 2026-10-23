//! Ignore-aware parallel repository walk (architecture.md section 3, D30).
//!
//! [`walk`] lists every non-ignored file under a root with its size, blake3
//! digest and a language guess, sorted by relative path so two walks of the
//! same tree are identical. Files above the size cap are reported in
//! [`WalkResult::oversized`] without being read.
//!
//! Digests and sizes are over the content as git would store it ([`ContentSource`]): clean
//! filters such as `core.autocrlf` are applied, so a CRLF checkout hashes like its LF twin.
//!
//! The [`selector`] module parses the grmb-spec 6 selector grammar and evaluates it over the walk
//! ([`select_files`]); gob-ir evaluates the same selectors over units. [`owner`] resolves which
//! entity owns an item by [`Specificity`] and the possible-worlds reading of binding.md 2.2.

use std::fmt;
use std::path::Path;
use std::sync::Mutex;

use ignore::overrides::OverrideBuilder;
use ignore::{WalkBuilder, WalkState};
use rayon::prelude::*;

mod content;
mod generated;
pub mod owner;
mod role;
mod select;
pub mod selector;
mod specificity;

pub use content::{
    BackendError, ContentBackend, ContentLocator, ContentReader, ContentSource, FileReader,
    install_backend,
};
pub use generated::{GENERATED_DIRS, GeneratedDir};
pub use owner::{Candidate, EntityName, MatchStatus, Owner, Ownership};
pub use role::{DEFAULT_LEDGER_DIR, FileRole, Roles};
pub use select::{PathMatch, owner_of_path, select_files, unseen_files};
pub use selector::{Glob, Selector, wildcard_match};
pub use specificity::Specificity;

/// Errors raised before or during a walk.
#[derive(Debug, thiserror::Error)]
pub enum WalkError {
    /// An exclude glob could not be compiled.
    #[error("E-WALK-GLOB: invalid exclude glob `{glob}`: {source}")]
    BadGlob {
        /// The offending glob.
        glob: String,
        /// Underlying parse error.
        source: ignore::Error,
    },
}

/// A blake3 content digest, displayed as 64 lowercase hex characters.
#[derive(Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Debug)]
pub struct Digest([u8; 32]);

impl Digest {
    /// Hashes `bytes`.
    pub fn of(bytes: &[u8]) -> Self {
        Self(*blake3::hash(bytes).as_bytes())
    }

    /// Returns the raw 32 digest bytes.
    pub fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

impl fmt::Display for Digest {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        for b in self.0 {
            write!(f, "{b:02x}")?;
        }
        Ok(())
    }
}

/// Language guess derived from a file extension.
#[derive(Clone, PartialEq, Eq, Hash, Debug)]
pub enum LanguageHint {
    /// `.rs`
    Rust,
    /// `.md`, `.markdown`
    Markdown,
    /// `.toml`
    Toml,
    /// Any other extension (lowercased, possibly empty).
    Other(String),
}

impl LanguageHint {
    /// The language tag used by `lang(...)` predicates (`rust`, `markdown`, `toml`, or the extension).
    pub fn tag(&self) -> &str {
        match self {
            Self::Rust => "rust",
            Self::Markdown => "markdown",
            Self::Toml => "toml",
            Self::Other(ext) => ext,
        }
    }

    /// Guesses the language of `path` from its extension alone.
    pub fn from_path(path: &str) -> Self {
        let ext = Path::new(path)
            .extension()
            .and_then(gob_path::exact_text)
            .unwrap_or("")
            .to_ascii_lowercase();
        match ext.as_str() {
            "rs" => Self::Rust,
            "md" | "markdown" => Self::Markdown,
            "toml" => Self::Toml,
            _ => Self::Other(ext),
        }
    }
}

/// Walk knobs: the `[check] exclude` globs and the size cap.
#[derive(Clone, Debug)]
pub struct WalkConfig {
    /// Gitignore-style globs to exclude in addition to ignore files.
    pub exclude: Vec<String>,
    /// Files strictly larger than this many bytes are reported as oversized.
    pub size_cap: u64,
    /// Whether to follow symlinks (default false).
    pub follow_links: bool,
}

impl Default for WalkConfig {
    fn default() -> Self {
        Self {
            exclude: Vec::new(),
            size_cap: 4 * 1024 * 1024,
            follow_links: false,
        }
    }
}

/// One walked file.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct FileEntry {
    /// Path relative to the root, forward-slash separated.
    pub path: String,
    /// Size in bytes.
    pub size: u64,
    /// blake3 digest of the content.
    pub digest: Digest,
    /// Language guess by extension.
    pub language: LanguageHint,
}

/// A file skipped because it exceeds the size cap (an Unresolved marker).
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct Oversized {
    /// Path relative to the root, forward-slash separated.
    pub path: String,
    /// Size in bytes.
    pub size: u64,
}

/// Result of a walk; both lists are sorted by path.
#[derive(Clone, Default, PartialEq, Eq, Debug)]
pub struct WalkResult {
    /// Hashed files.
    pub files: Vec<FileEntry>,
    /// Files above the size cap.
    pub oversized: Vec<Oversized>,
}

enum Item {
    /// Under the cap; read and hashed after the walk through the content source.
    Pending(String, u64),
    Big(Oversized),
}

/// `path` relative to `root` as `/`-separated text; the lossy display form when it cannot be a `RelPath`.
fn rel_path(root: &Path, path: &Path) -> String {
    gob_path::RelPath::from_host(root, path).map_or_else(
        |_| {
            let rel = path.strip_prefix(root).unwrap_or(path);
            gob_path::Shown::with_home(rel, None).to_string()
        },
        |r| r.as_str().to_owned(),
    )
}

/// Tool state directories no walk ever enters, whatever the config says.
pub const STATE_DIRS: [&str; 3] = [".git", ".frob", ".grimble"];

/// True for `.git` (file or directory, as in a linked worktree) and for `.frob/` and `.grimble/` directories.
fn is_state_entry(e: &ignore::DirEntry) -> bool {
    let name = e.file_name();
    if name == ".git" {
        return true;
    }
    e.file_type().is_some_and(|t| t.is_dir()) && STATE_DIRS.iter().any(|d| name == *d)
}

/// Files read per filter pipeline (building one loads the index and attributes).
const READ_CHUNK: usize = 256;

// frob:ticket 01M4DPJR7RFS40YTGVT80A3EXX
/// Lists the files under the cap (path, size) and the oversized ones; reads no content.
fn list(root: &Path, config: &WalkConfig) -> Result<(Vec<(String, u64)>, WalkResult), WalkError> {
    let rules = generated::active_rules(&config.exclude);
    let mut ob = OverrideBuilder::new(root);
    for glob in config.exclude.iter().filter(|g| !g.starts_with('!')) {
        ob.add(&format!("!{glob}"))
            .map_err(|source| WalkError::BadGlob {
                glob: glob.clone(),
                source,
            })?;
    }
    let overrides = ob.build().map_err(|source| WalkError::BadGlob {
        glob: config.exclude.join(","),
        source,
    })?;

    let mut builder = WalkBuilder::new(root);
    builder
        .hidden(false)
        .require_git(false)
        .follow_links(config.follow_links)
        .overrides(overrides)
        .filter_entry(move |e| {
            let generated = e.file_type().is_some_and(|t| t.is_dir())
                && generated::is_generated(&rules, e.path());
            !(is_state_entry(e) || generated)
        });

    let items: Mutex<Vec<Item>> = Mutex::new(Vec::new());
    let cap = config.size_cap;
    builder.build_parallel().run(|| {
        let items = &items;
        Box::new(move |res| {
            let entry = match res {
                Ok(e) => e,
                Err(err) => {
                    tracing::warn!(%err, "walk entry error");
                    return WalkState::Continue;
                }
            };
            if !entry.file_type().is_some_and(|t| t.is_file()) {
                return WalkState::Continue;
            }
            let path = rel_path(root, entry.path());
            let size = match entry.metadata() {
                Ok(m) => m.len(),
                Err(err) => {
                    tracing::warn!(%err, path, "stat failed; skipping");
                    return WalkState::Continue;
                }
            };
            let item = if size > cap {
                tracing::debug!(path, size, cap, "oversized file");
                Item::Big(Oversized { path, size })
            } else {
                Item::Pending(path, size)
            };
            items
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .push(item);
            WalkState::Continue
        })
    });

    let mut out = WalkResult::default();
    let mut pending = Vec::new();
    for item in items
        .into_inner()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
    {
        match item {
            Item::Pending(p, size) => pending.push((p, size)),
            Item::Big(b) => out.oversized.push(b),
        }
    }
    Ok((pending, out))
}

// frob:ticket 01M4DPJR7RFS40YTGVT80A3EXX
/// One file of a path-only walk.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct PathEntry {
    /// Path relative to the root, forward-slash separated.
    pub path: String,
    /// Size in bytes on disk (not the git-normalized size).
    pub size: u64,
}

// frob:ticket 01M4DPJR7RFS40YTGVT80A3EXX
/// Result of [`walk_paths`]; both lists are sorted by path.
#[derive(Clone, Default, PartialEq, Eq, Debug)]
pub struct PathWalkResult {
    /// Files under the size cap, listed but never read.
    pub files: Vec<PathEntry>,
    /// Files above the size cap.
    pub oversized: Vec<Oversized>,
}

// frob:ticket 01M4DPJR7RFS40YTGVT80A3EXX
/// Like [`walk`] but lists paths and on-disk sizes only: no file is read, filtered or hashed.
///
/// Use it when the caller reads the files itself or needs only their names.
///
/// # Errors
/// Returns [`WalkError::BadGlob`] when an exclude glob does not compile.
pub fn walk_paths(root: &Path, config: &WalkConfig) -> Result<PathWalkResult, WalkError> {
    let (listing, mut out) = list(root, config)?;
    let mut files: Vec<PathEntry> = listing
        .into_iter()
        .map(|(path, size)| PathEntry { path, size })
        .collect();
    files.sort_by(|a, b| a.path.cmp(&b.path));
    out.oversized.sort_by(|a, b| a.path.cmp(&b.path));
    tracing::info!(
        files = files.len(),
        oversized = out.oversized.len(),
        "path walk complete"
    );
    Ok(PathWalkResult {
        files,
        oversized: out.oversized,
    })
}

/// Walks `root` in parallel honoring ignore files and `config.exclude`.
///
/// The state directories [`STATE_DIRS`] (`.git/`, `.frob/`, `.grimble/`) are always
/// skipped, with or without an exclude entry, so no product reports another's cache.
///
/// # Errors
/// Returns [`WalkError::BadGlob`] when an exclude glob does not compile.
/// Unreadable files are logged at warn and skipped.
pub fn walk(root: &Path, config: &WalkConfig) -> Result<WalkResult, WalkError> {
    walk_with(root, config, &ContentSource::locate(root))
}

// frob:ticket 01M4Q3A2SA49G06ZVAN753TYM2
/// Like [`walk`], but reads content through the injected `source` instead of the installed backend.
///
/// # Errors
/// Returns [`WalkError::BadGlob`] when an exclude glob does not compile.
pub fn walk_with(
    root: &Path,
    config: &WalkConfig,
    source: &ContentSource,
) -> Result<WalkResult, WalkError> {
    // frob:ticket 01M4DPJR7RFS40YTGVT80A3EXX
    let (listing, mut out) = list(root, config)?;
    let pending: Vec<String> = listing.into_iter().map(|(path, _)| path).collect();
    // Digests are over the content as git would store it (clean filters applied),
    // so a CRLF checkout under core.autocrlf hashes like its LF twin.
    out.files = pending
        .par_chunks(READ_CHUNK)
        .flat_map_iter(|chunk| {
            source.with_reader(|reader| {
                chunk
                    .iter()
                    .filter_map(|path| match reader.read(path) {
                        Ok(bytes) => Some(FileEntry {
                            language: LanguageHint::from_path(path),
                            digest: Digest::of(&bytes),
                            size: bytes.len() as u64,
                            path: path.clone(),
                        }),
                        Err(err) => {
                            tracing::warn!(%err, path, "read failed; skipping");
                            None
                        }
                    })
                    .collect::<Vec<_>>()
            })
        })
        .collect();
    out.files.sort_by(|a, b| a.path.cmp(&b.path));
    out.oversized.sort_by(|a, b| a.path.cmp(&b.path));
    tracing::info!(
        files = out.files.len(),
        oversized = out.oversized.len(),
        "walk complete"
    );
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn write(root: &Path, rel: &str, body: &str) {
        let p = root.join(rel);
        fs::create_dir_all(p.parent().unwrap()).unwrap();
        fs::write(p, body).unwrap();
    }

    fn paths(r: &WalkResult) -> Vec<&str> {
        r.files.iter().map(|f| f.path.as_str()).collect()
    }

    #[derive(Debug)]
    struct FakeLocator;

    struct FakeReader;

    impl FileReader for FakeReader {
        fn read(&mut self, rel: &str) -> Result<Option<Vec<u8>>, BackendError> {
            Ok(Some(format!("fake:{rel}").into_bytes()))
        }
    }

    impl ContentLocator for FakeLocator {
        fn with_reader(&self, f: &mut dyn FnMut(&mut dyn FileReader)) {
            f(&mut FakeReader);
        }
    }

    // frob:tests crates/gob-walk/src/lib.rs::walk_with
    #[test]
    fn a_fake_reader_drives_a_walk_without_any_git_backend() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write(root, "a.rs", "on disk");
        let source = ContentSource::with_locator(root, std::sync::Arc::new(FakeLocator));
        let found = walk_with(root, &WalkConfig::default(), &source).unwrap();
        assert_eq!(paths(&found), ["a.rs"]);
        assert_eq!(found.files[0].digest, Digest::of(b"fake:a.rs"));
    }

    #[test]
    fn gitignore_excludes_target_and_order_is_stable() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write(root, ".gitignore", "target/\n");
        write(root, "target/debug/x.rs", "x");
        write(root, "src/b.rs", "b");
        write(root, "src/a.rs", "a");
        write(root, "README.md", "r");
        let cfg = WalkConfig::default();
        let one = walk(root, &cfg).unwrap();
        let two = walk(root, &cfg).unwrap();
        assert_eq!(one, two);
        assert!(one.files.iter().all(|f| !f.path.starts_with("target/")));
        assert_eq!(
            paths(&one),
            [".gitignore", "README.md", "src/a.rs", "src/b.rs"]
        );
        assert_eq!(one.files[2].language, LanguageHint::Rust);
        assert_eq!(one.files[1].language, LanguageHint::Markdown);
    }

    // frob:tests crates/gob-walk/src/lib.rs::walk
    #[test]
    fn state_directories_are_never_walked_without_any_config() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write(root, ".frob/cache/x.json", "x");
        write(root, ".grimble/state.json", "x");
        write(root, ".git/config", "x");
        write(root, "crates/a/.frob/y", "x");
        write(root, ".frobrc", "kept");
        write(root, "src/a.rs", "a");
        let found = walk(root, &WalkConfig::default()).unwrap();
        assert_eq!(paths(&found), [".frobrc", "src/a.rs"]);
    }

    // frob:ticket 01M4GKCSFB13Y0VH1E1DDTA99H
    // frob:tests crates/gob-walk/src/lib.rs::walk
    #[test]
    fn generated_report_dirs_are_skipped_by_default_and_opt_in_works() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write(root, "coverage/index.html", "<html>");
        write(root, "coverage/base.css", "x");
        write(root, "coverage/lcov-report/a.js.html", "x");
        write(root, "pkg/web/coverage/prettify.js", "x");
        write(root, "playwright-report/index.html", "x");
        write(root, "htmlcov/index.html", "x");
        write(root, "src/coverage/mod.rs", "legit source");
        write(root, "docs/htmlcov/notes.md", "no marker, kept");
        write(root, "src/a.rs", "a");
        let found = walk(root, &WalkConfig::default()).unwrap();
        assert_eq!(
            paths(&found),
            ["docs/htmlcov/notes.md", "src/a.rs", "src/coverage/mod.rs"]
        );
        let cfg = WalkConfig {
            exclude: vec!["!coverage/".into(), "!playwright-report".into()],
            ..WalkConfig::default()
        };
        let binding = walk(root, &cfg).unwrap();
        let opted = paths(&binding);
        assert!(opted.contains(&"coverage/index.html"));
        assert!(opted.contains(&"pkg/web/coverage/prettify.js"));
        assert!(opted.contains(&"playwright-report/index.html"));
        assert!(!opted.contains(&"htmlcov/index.html"));
    }

    #[test]
    fn config_exclude_and_bad_glob() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write(root, "gen/out.rs", "x");
        write(root, "keep.toml", "k");
        let cfg = WalkConfig {
            exclude: vec!["gen/".into()],
            ..WalkConfig::default()
        };
        assert_eq!(paths(&walk(root, &cfg).unwrap()), ["keep.toml"]);
        let bad = WalkConfig {
            exclude: vec!["[".into()],
            ..WalkConfig::default()
        };
        assert!(matches!(walk(root, &bad), Err(WalkError::BadGlob { .. })));
    }

    #[test]
    fn oversized_files_are_reported_not_hashed() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write(root, "big.bin", "0123456789");
        write(root, "small.txt", "01");
        let cfg = WalkConfig {
            size_cap: 5,
            ..WalkConfig::default()
        };
        let r = walk(root, &cfg).unwrap();
        assert_eq!(paths(&r), ["small.txt"]);
        assert_eq!(
            r.oversized,
            [Oversized {
                path: "big.bin".into(),
                size: 10
            }]
        );
    }

    #[test]
    fn digest_is_hex_and_content_addressed() {
        let d = Digest::of(b"a");
        assert_eq!(d.to_string().len(), 64);
        assert_eq!(d, Digest::of(b"a"));
        assert_ne!(d, Digest::of(b"b"));
        assert_eq!(
            LanguageHint::from_path("x.PY"),
            LanguageHint::Other("py".into())
        );
    }
}
