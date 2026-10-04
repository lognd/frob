//! The walk: the product-neutral inputs every run starts from.

use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::time::Instant;

use gob_symbols::{SkipKind, SkippedFile};
use gob_text::{FileId, FileInterner};
use gob_walk::{FileEntry, WalkConfig, walk};

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
    })
}
