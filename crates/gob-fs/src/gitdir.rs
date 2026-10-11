//! The git common directory of a checkout, read from the filesystem.

// frob:ticket 01M4M52WKHGXADHPQ08J1AS8BJ

use std::path::{Path, PathBuf};

/// The git common directory of the checkout at `root`, read from the filesystem (no git process).
///
/// A primary checkout has a `.git` directory; a linked worktree has a `.git` file naming its
/// private git dir, whose `commondir` file points back at the shared one. Both branches return
/// the [`canonical`](crate::canonical) form so the two spellings of one directory (8.3 short vs
/// long name on Windows) agree.
pub fn git_common_dir(root: &Path) -> Option<PathBuf> {
    let dot_git = root.join(".git");
    let meta = std::fs::metadata(&dot_git).ok()?;
    if meta.is_dir() {
        return crate::canonical(&dot_git).ok();
    }
    let text = std::fs::read_to_string(&dot_git).ok()?;
    let private = Path::new(text.trim().strip_prefix("gitdir:")?.trim());
    let private = if private.is_absolute() {
        private.to_path_buf()
    } else {
        root.join(private)
    };
    let common = match std::fs::read_to_string(private.join("commondir")) {
        Ok(rel) => private.join(rel.trim()),
        Err(_) => private,
    };
    crate::canonical(&common).ok()
}
