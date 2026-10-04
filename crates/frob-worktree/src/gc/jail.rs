//! The path discipline of every deletion: admit a path only inside a known root.
//!
//! Roots are canonicalised once. A candidate is admitted when it is absolute, free of
//! `..`, is not itself a symlink, and its canonical form lies strictly below a root
//! (compared by components through [`Path::starts_with`], never by string prefix, so
//! `/a/target-old` is not inside `/a/target`). A path that reaches outside through a
//! symlinked parent canonicalises outside the roots and is refused. The admitted,
//! canonical path is what callers delete, so no check is made on one path and the
//! delete on another.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::path::{Component, Path, PathBuf};

/// Why a path was not admitted.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum JailError {
    /// The path is relative or contains `..`.
    #[error("{0} is not an absolute path without `..` components")]
    NotAbsolute(PathBuf),
    /// The path itself is a symlink; frob never deletes through or instead of one.
    #[error("{0} is a symlink")]
    Symlink(PathBuf),
    /// The path cannot be resolved (missing or unreadable).
    #[error("{path} cannot be resolved: {reason}")]
    Unresolvable {
        /// The path asked about.
        path: PathBuf,
        /// The OS error text.
        reason: String,
    },
    /// The path resolves outside every root, or is a root itself.
    #[error("{0} is outside the directories frob may collect")]
    Outside(PathBuf),
}

/// A set of canonical roots that deletions must stay strictly below.
#[derive(Debug, Clone, Default)]
pub struct Jail {
    roots: Vec<PathBuf>,
}

impl Jail {
    /// A jail over `roots`; a root that does not exist is dropped (nothing can be below it).
    pub fn new(roots: impl IntoIterator<Item = PathBuf>) -> Self {
        let roots = roots
            .into_iter()
            .filter_map(|r| match r.canonicalize() {
                Ok(c) => Some(c),
                Err(e) => {
                    tracing::debug!(root = %r.display(), error = %e, "gc root absent; dropped");
                    None
                }
            })
            .collect();
        Self { roots }
    }

    /// The canonical roots.
    pub fn roots(&self) -> &[PathBuf] {
        &self.roots
    }

    /// The canonical form of `path` when it may be deleted, else the reason it may not.
    ///
    /// # Errors
    ///
    /// A [`JailError`] for a relative or `..` path, a symlink, an unresolvable path
    /// or one that resolves outside (or equal to) every root.
    pub fn admit(&self, path: &Path) -> Result<PathBuf, JailError> {
        if !path.is_absolute() || path.components().any(|c| c == Component::ParentDir) {
            return Err(JailError::NotAbsolute(path.to_path_buf()));
        }
        let meta = std::fs::symlink_metadata(path).map_err(|e| JailError::Unresolvable {
            path: path.to_path_buf(),
            reason: e.to_string(),
        })?;
        if meta.file_type().is_symlink() {
            return Err(JailError::Symlink(path.to_path_buf()));
        }
        let canon = path.canonicalize().map_err(|e| JailError::Unresolvable {
            path: path.to_path_buf(),
            reason: e.to_string(),
        })?;
        if self
            .roots
            .iter()
            .any(|r| canon.starts_with(r) && canon != *r)
        {
            Ok(canon)
        } else {
            tracing::warn!(path = %path.display(), resolved = %canon.display(), "gc refused a path outside its roots");
            Err(JailError::Outside(path.to_path_buf()))
        }
    }

    /// Delete the tree at `path` after admitting it; returns the canonical path removed.
    ///
    /// `std::fs::remove_dir_all` unlinks a symlink inside the tree instead of
    /// following it, so nothing outside the admitted tree is touched.
    ///
    /// # Errors
    ///
    /// The [`JailError`] when not admitted, or the OS error text when deleting fails.
    pub fn remove(&self, path: &Path) -> Result<PathBuf, String> {
        let canon = self.admit(path).map_err(|e| e.to_string())?;
        let meta = std::fs::symlink_metadata(&canon).map_err(|e| e.to_string())?;
        let result = if meta.is_dir() {
            std::fs::remove_dir_all(&canon)
        } else {
            std::fs::remove_file(&canon)
        };
        match result {
            Ok(()) => {
                tracing::info!(path = %canon.display(), "gc removed");
                Ok(canon)
            }
            Err(e) => {
                tracing::warn!(path = %canon.display(), error = %e, "gc removal failed");
                Err(format!("{}: {e}", canon.display()))
            }
        }
    }
}
