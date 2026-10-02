//! `FileId`, a simple interner for it, and `Span`.

use std::collections::HashMap;
use std::fmt;

use crate::size::TextRange;

/// An interned file identity; cheap to copy and compare.
///
/// Ids are only meaningful relative to the [`FileInterner`] that made them.
///
/// ```
/// use gob_text::FileInterner;
/// let mut files = FileInterner::new();
/// let a = files.intern("src/a.rs");
/// assert_eq!(a, files.intern("src/a.rs"));
/// assert_ne!(a, files.intern("src/b.rs"));
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct FileId(u32);

impl FileId {
    /// The dense index of this id inside its interner.
    pub const fn index(self) -> u32 {
        self.0
    }
}

impl fmt::Display for FileId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "file#{}", self.0)
    }
}

/// Interns repo-relative path strings into [`FileId`]s.
///
/// ```
/// use gob_text::FileInterner;
/// let mut files = FileInterner::new();
/// let id = files.intern("a.md");
/// assert_eq!(files.path(id), Some("a.md"));
/// ```
#[derive(Debug, Default, Clone)]
pub struct FileInterner {
    paths: Vec<String>,
    ids: HashMap<String, FileId>,
}

impl FileInterner {
    /// An empty interner.
    pub fn new() -> Self {
        Self::default()
    }

    /// The id for `path`, allocating a new one on first sight.
    ///
    /// # Panics
    ///
    /// Panics if more than `u32::MAX` distinct files are interned.
    pub fn intern(&mut self, path: &str) -> FileId {
        if let Some(id) = self.ids.get(path) {
            return *id;
        }
        let id = FileId(u32::try_from(self.paths.len()).expect("too many files interned"));
        self.paths.push(path.to_owned());
        self.ids.insert(path.to_owned(), id);
        id
    }

    /// The path an id was interned from.
    pub fn path(&self, id: FileId) -> Option<&str> {
        self.paths.get(id.0 as usize).map(String::as_str)
    }

    /// Number of distinct files interned.
    pub fn len(&self) -> usize {
        self.paths.len()
    }

    /// Whether nothing has been interned.
    pub fn is_empty(&self) -> bool {
        self.paths.is_empty()
    }
}

/// A byte range within a specific file.
///
/// ```
/// use gob_text::{FileInterner, Span, TextRange};
/// let mut files = FileInterner::new();
/// let span = Span::new(files.intern("a.rs"), TextRange::new(1u32.into(), 3u32.into()));
/// assert_eq!(span.range.len(), 2u32.into());
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Span {
    /// The file the range refers to.
    pub file: FileId,
    /// Byte range inside that file.
    pub range: TextRange,
}

impl Span {
    /// Pair a file with a range.
    pub const fn new(file: FileId, range: TextRange) -> Self {
        Self { file, range }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dense_ids_and_lookup() {
        let mut f = FileInterner::new();
        let a = f.intern("a");
        let b = f.intern("b");
        assert_eq!((a.index(), b.index()), (0, 1));
        assert_eq!(f.intern("a"), a);
        assert_eq!(f.len(), 2);
        assert_eq!(f.path(b), Some("b"));
        assert_eq!(f.path(FileId(9)), None);
    }
}
