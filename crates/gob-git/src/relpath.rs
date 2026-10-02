//! Validated repo-relative paths for ledger writes.

use crate::GitError;

/// A slash-separated, repo-relative path with no `.`, `..`, empty or absolute components.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct RelPath(String);

impl RelPath {
    /// Validate `s` as a repo-relative path.
    ///
    /// # Errors
    /// [`GitError::BadPath`] for empty, absolute, backslashed or dot-segment paths.
    pub fn new(s: impl Into<String>) -> Result<Self, GitError> {
        let s = s.into();
        let ok = !s.is_empty()
            && !s.starts_with('/')
            && !s.contains('\\')
            && !s.contains('\0')
            && s.split('/')
                .all(|c| !c.is_empty() && c != "." && c != ".." && c != ".git");
        if ok {
            Ok(Self(s))
        } else {
            Err(GitError::BadPath(s))
        }
    }

    /// The path as a slash-separated string.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl std::fmt::Display for RelPath {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}
