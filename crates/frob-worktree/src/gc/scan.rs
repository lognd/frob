//! Size and recency of a tree, never following symlinks.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::path::Path;
use std::time::SystemTime;

/// Total bytes and newest modification time under (or of) a path.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Scan {
    /// Sum of the file lengths (a symlink counts as itself, not its target).
    pub bytes: u64,
    /// Latest modification time of any entry, `None` for an empty or unreadable path.
    pub newest: Option<SystemTime>,
}

impl Scan {
    /// Fold `other` into `self`.
    pub fn merge(&mut self, other: Self) {
        self.bytes = self.bytes.saturating_add(other.bytes);
        self.newest = self.newest.max(other.newest);
    }
}

/// Measure `path`; unreadable entries are skipped (logged at debug), so the figure may undercount.
pub fn scan(path: &Path) -> Scan {
    let mut total = Scan::default();
    let mut stack = vec![path.to_path_buf()];
    while let Some(p) = stack.pop() {
        let meta = match std::fs::symlink_metadata(&p) {
            Ok(m) => m,
            Err(e) => {
                tracing::debug!(path = %p.display(), error = %e, "scan skipped an entry");
                continue;
            }
        };
        total.bytes = total.bytes.saturating_add(meta.len());
        total.newest = total.newest.max(meta.modified().ok());
        if meta.is_dir() {
            match std::fs::read_dir(&p) {
                Ok(rd) => stack.extend(rd.filter_map(Result::ok).map(|e| e.path())),
                Err(e) => tracing::debug!(path = %p.display(), error = %e, "scan could not list"),
            }
        }
    }
    total
}
