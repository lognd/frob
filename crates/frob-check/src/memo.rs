//! Content-addressed store of finished `[[check.tool]]` results, shared by every worktree.
//!
//! Records live under `<git common dir>/frob/check-results/<key>.json`; the key already hashes
//! the stage's inputs, command and version window, so a record is valid for any checkout
//! (frob:ticket 01M4MH624WYQHRVHT9B3K1MDJD).

use std::path::{Path, PathBuf};

use gob_check::ToolMemo;

/// A [`ToolMemo`] backed by one file per key.
#[derive(Debug, Clone)]
pub struct FileToolMemo {
    dir: PathBuf,
}

impl FileToolMemo {
    /// A store rooted at `dir` (created on first write).
    pub fn at(dir: impl Into<PathBuf>) -> Self {
        Self { dir: dir.into() }
    }

    /// The shared store of the repository containing `root`; `None` outside a repository.
    pub fn for_repo(root: &Path) -> Option<Self> {
        let repo = gob_git::Repo::discover(root).ok()?;
        Some(Self::at(
            repo.common_dir().join("frob").join("check-results"),
        ))
    }

    fn path(&self, key: &str) -> Option<PathBuf> {
        // Keys are hex digests; refuse anything that could leave the directory.
        key.bytes()
            .all(|b| b.is_ascii_hexdigit())
            .then(|| self.dir.join(format!("{key}.json")))
    }
}

#[allow(
    clippy::disallowed_methods,
    reason = "tool memo entries are cache files under the state dir, not walked sources"
)]
impl ToolMemo for FileToolMemo {
    fn load(&self, key: &str) -> Option<String> {
        std::fs::read_to_string(self.path(key)?).ok()
    }

    fn store(&self, key: &str, payload: &str) {
        let Some(path) = self.path(key) else { return };
        let written = std::fs::create_dir_all(&self.dir)
            .and_then(|()| gob_fs::write_atomic(&path, payload.as_bytes()));
        if let Err(e) = written {
            tracing::warn!(error = %e, "tool result not recorded");
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn records_round_trip_and_odd_keys_are_refused() {
        let dir = tempfile::tempdir().expect("tempdir");
        let memo = FileToolMemo::at(dir.path().join("r"));
        assert_eq!(memo.load("abc123"), None);
        memo.store("abc123", "[]");
        assert_eq!(memo.load("abc123").as_deref(), Some("[]"));
        memo.store("../x", "[]");
        assert_eq!(memo.load("../x"), None);
    }
}
