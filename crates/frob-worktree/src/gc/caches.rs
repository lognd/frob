//! Regenerable caches under a checkout's `.frob/`, evicted least-recently-used over a budget.
//!
//! An allowlist, not a sweep: only `cache.sqlite` (with its `-wal`, `-shm` and
//! `-journal` companions) and the per-commit files in `land-base/` are caches that
//! frob rebuilds on demand. Lock files, the ticket index, journals and repair state
//! are never touched. A cache modified within the last hour may be open in another
//! process and is left alone.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

use super::scan::scan;

/// A cache entry modified within this window may be in use and is never evicted.
const IN_USE_WINDOW: Duration = Duration::from_secs(3600);

/// One evictable cache entry.
#[derive(Debug, Clone)]
pub struct Entry {
    /// Files removed together (a database and its companions, or one `land-base` file).
    pub paths: Vec<PathBuf>,
    /// Their total size.
    pub bytes: u64,
    /// Their latest modification time.
    pub modified: SystemTime,
}

/// The cache entries of the checkout at `root`.
pub fn entries(root: &Path) -> Vec<Entry> {
    let dir = root.join(".frob");
    let mut out = Vec::new();
    let db: Vec<PathBuf> = [
        "cache.sqlite",
        "cache.sqlite-wal",
        "cache.sqlite-shm",
        "cache.sqlite-journal",
    ]
    .iter()
    .map(|n| dir.join(n))
    .filter(|p| std::fs::symlink_metadata(p).is_ok_and(|m| m.is_file()))
    .collect();
    if !db.is_empty() {
        out.push(entry_of(db));
    }
    if let Ok(rd) = std::fs::read_dir(dir.join("land-base")) {
        for e in rd.filter_map(Result::ok) {
            if e.file_type().is_ok_and(|t| t.is_file()) {
                out.push(entry_of(vec![e.path()]));
            }
        }
    }
    out
}

fn entry_of(paths: Vec<PathBuf>) -> Entry {
    let mut total = super::scan::Scan::default();
    for p in &paths {
        total.merge(scan(p));
    }
    Entry {
        paths,
        bytes: total.bytes,
        modified: total.newest.unwrap_or(SystemTime::UNIX_EPOCH),
    }
}

/// Total bytes of `entries`.
pub fn total(entries: &[Entry]) -> u64 {
    entries.iter().map(|e| e.bytes).sum()
}

/// The entries to evict to bring `entries` within `budget` bytes: least recently modified first, never one in use.
pub fn plan(mut entries: Vec<Entry>, budget: u64, now: SystemTime) -> Vec<Entry> {
    let mut size = total(&entries);
    entries.sort_by_key(|e| e.modified);
    let mut evict = Vec::new();
    for e in entries {
        if size <= budget {
            break;
        }
        if now.duration_since(e.modified).unwrap_or_default() < IN_USE_WINDOW {
            continue;
        }
        size = size.saturating_sub(e.bytes);
        evict.push(e);
    }
    evict
}
