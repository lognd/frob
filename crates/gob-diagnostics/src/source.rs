//! Source lookup used to turn byte spans into lines, columns and snippets.

use std::collections::HashMap;

use gob_text::{FileId, SourceText};

/// Supplies file paths and contents (hence line indexes) for a `FileId`.
pub trait SourceProvider {
    /// Display path of `file`, if known.
    fn path(&self, file: FileId) -> Option<&str>;
    /// Contents of `file` with its line index, if available.
    fn source(&self, file: FileId) -> Option<&SourceText>;
}

/// In-memory [`SourceProvider`], used by tests and small callers.
#[derive(Debug, Default)]
pub struct MemorySources {
    files: HashMap<FileId, (String, SourceText)>,
}

impl MemorySources {
    /// An empty provider.
    pub fn new() -> Self {
        Self::default()
    }

    /// Register `file` under `path` with `text`.
    pub fn insert(&mut self, file: FileId, path: impl Into<String>, text: SourceText) {
        let path = path.into();
        tracing::debug!(%file, %path, "source registered");
        self.files.insert(file, (path, text));
    }
}

impl SourceProvider for MemorySources {
    fn path(&self, file: FileId) -> Option<&str> {
        self.files.get(&file).map(|(p, _)| p.as_str())
    }

    fn source(&self, file: FileId) -> Option<&SourceText> {
        self.files.get(&file).map(|(_, s)| s)
    }
}
