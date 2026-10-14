//! The walk: the product-neutral inputs every run starts from.

use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::time::Instant;

use gob_symbols::{SkipKind, SkippedFile};
use gob_text::{FileId, FileInterner};
use gob_walk::{ContentReader, ContentSource, FileEntry, WalkConfig, walk};

use crate::config::CheckTable;
use crate::error::CheckError;
use crate::report::{Stats, Timing};

/// Read-only, thread-safe facts about the walked files.
#[derive(Debug, Default)]
pub struct FileIndex {
    /// Interned id per repo-relative path.
    pub ids: HashMap<String, FileId>,
    /// Hex content digest per path.
    pub digests: HashMap<String, String>,
    /// Every ancestor directory of a walked file (links to directories resolve).
    pub dirs: HashSet<String>,
}

// frob:ticket 01M42M1KK02KFZG39CXKAD47SZ
/// What the walk produced: the repository root, its files and their identities.
#[derive(Debug)]
pub struct Core {
    /// Repository root.
    pub root: PathBuf,
    /// Walked files, sorted by path.
    pub entries: Vec<FileEntry>,
    /// Path lookups.
    pub index: FileIndex,
    /// Interner holding every walked path; products extend clones of it.
    pub files: FileInterner,
    /// Walked files over `size_cap`: never read, reported as Unresolved (`READ001`).
    pub skipped: Vec<SkippedFile>,
    /// Where walked content is read from: the same normal form the digests were taken over.
    content: ContentSource,
}

impl Core {
    /// Runs `f` with a content reader over the walk; batch reads here so a repository opens once.
    pub fn with_content<T>(&self, f: impl FnOnce(&mut ContentReader<'_, '_>) -> T) -> T {
        self.content.with_reader(f)
    }

    /// The walked content of `rel` as bytes (rules read this, never the disk).
    ///
    /// # Errors
    /// [`std::io::ErrorKind::NotFound`] when absent, other I/O errors as the OS reports them.
    pub fn bytes(&self, rel: &str) -> std::io::Result<Vec<u8>> {
        self.with_content(|r| r.read(rel))
    }

    /// The walked content of `rel` as UTF-8 text.
    ///
    /// # Errors
    /// [`std::io::ErrorKind::InvalidData`] when not UTF-8, otherwise as [`Core::bytes`].
    pub fn text(&self, rel: &str) -> std::io::Result<String> {
        self.with_content(|r| r.read_text(rel))
    }
}

/// Walk `root` honouring `[check] exclude` and `size_cap`, never entering `/<state_dir>/` or `/target/`.
///
/// # Errors
///
/// [`CheckError::Walk`] for a bad exclude glob or an unreadable tree.
pub(crate) fn walk_core(
    root: &Path,
    table: &CheckTable,
    state_dir: &str,
    timing: &mut Timing,
    stats: &mut Stats,
) -> Result<Core, CheckError> {
    let started = Instant::now();
    let mut exclude = vec![format!("/{state_dir}/"), "/target/".to_owned()];
    exclude.extend(table.exclude.iter().cloned());
    let walked = walk(
        root,
        &WalkConfig {
            exclude,
            size_cap: table.size_cap,
            ..WalkConfig::default()
        },
    )?;
    let skipped: Vec<SkippedFile> = walked
        .oversized
        .iter()
        .map(|big| {
            tracing::info!(path = %big.path, size = big.size, "file over size_cap; reported as READ001");
            SkippedFile {
                path: big.path.clone(),
                kind: SkipKind::Size,
                detail: format!("{} bytes exceeds size_cap {}", big.size, table.size_cap),
            }
        })
        .collect();
    let mut entries = walked.files;
    entries.sort_by(|a, b| a.path.cmp(&b.path));
    let mut files = FileInterner::new();
    let mut index = FileIndex {
        ids: HashMap::with_capacity(entries.len()),
        digests: HashMap::with_capacity(entries.len()),
        dirs: HashSet::new(),
    };
    for e in &entries {
        index.ids.insert(e.path.clone(), files.intern(&e.path));
        index.digests.insert(e.path.clone(), e.digest.to_string());
        let mut dir = e.path.as_str();
        while let Some((parent, _)) = dir.rsplit_once('/') {
            if !index.dirs.insert(parent.to_owned()) {
                break;
            }
            dir = parent;
        }
    }
    stats.files = entries.len();
    timing.push("walk", started.elapsed(), true);
    Ok(Core {
        root: root.to_path_buf(),
        entries,
        index,
        files,
        skipped,
        content: ContentSource::locate(root),
    })
}

#[cfg(test)]
#[allow(
    clippy::disallowed_methods,
    reason = "a test writes its fixture straight to the scratch directory"
)]
mod tests {
    use super::*;
    use crate::report::{Stats, Timing};

    // frob:ticket 01M4CTE5SS3BGF5R4PP5A9VYZQ
    // frob:tests crates/gob-check/src/core.rs::Core.text
    // frob:tests crates/gob-check/src/core.rs::Core.bytes
    #[test]
    fn core_reads_walked_content_and_reports_absence() {
        let dir = tempfile::tempdir().expect("tempdir");
        std::fs::write(dir.path().join("a.txt"), "hello\n").expect("fixture");
        let core = walk_core(
            dir.path(),
            &CheckTable::default(),
            ".frob",
            &mut Timing::default(),
            &mut Stats::default(),
        )
        .expect("walk");
        assert_eq!(core.text("a.txt").expect("text"), "hello\n");
        assert_eq!(core.bytes("a.txt").expect("bytes"), b"hello\n");
        let missing = core.text("nope.txt").expect_err("absent file");
        assert_eq!(missing.kind(), std::io::ErrorKind::NotFound);
    }
}
