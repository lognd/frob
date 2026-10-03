//! File content as git would store it, so digests ignore checkout line-ending rewrites.

// frob:ticket 01M40THSWB75TFY8949M4T7MXR

use std::io;
use std::path::{Path, PathBuf};

use gob_git::{WorktreeReader, WorktreeSource};

/// Where file content is read from: git-normalized inside a checkout, raw bytes elsewhere.
#[derive(Debug, Clone)]
pub struct ContentSource {
    root: PathBuf,
    git: Option<WorktreeSource>,
}

/// Reads files of one [`ContentSource`]; reuses one filter pipeline across reads.
pub struct ContentReader<'a, 'r> {
    root: &'a Path,
    git: Option<&'a mut WorktreeReader<'r>>,
}

impl ContentSource {
    /// The source for `root`: git-normalized when `root` is inside a git checkout, raw otherwise.
    pub fn locate(root: &Path) -> Self {
        let git = WorktreeSource::locate(root);
        tracing::debug!(root = %root.display(), git = git.is_some(), "content source located");
        Self {
            root: root.to_path_buf(),
            git,
        }
    }

    /// Runs `f` with a reader; a repository that cannot be opened degrades to raw reads with a warning.
    pub fn with_reader<T>(&self, f: impl FnOnce(&mut ContentReader<'_, '_>) -> T) -> T {
        if let Some(git) = &self.git {
            return git.with_reader(|r| {
                f(&mut ContentReader {
                    root: &self.root,
                    git: Some(r),
                })
            });
        }
        f(&mut ContentReader {
            root: &self.root,
            git: None,
        })
    }
}

impl ContentReader<'_, '_> {
    /// The content of `rel` as git would store it.
    ///
    /// # Errors
    /// [`io::ErrorKind::NotFound`] when absent; other I/O errors as the OS reports them.
    /// A failing filter pipeline falls back to the raw bytes (logged at warn).
    pub fn read(&mut self, rel: &str) -> io::Result<Vec<u8>> {
        if let Some(git) = self.git.as_deref_mut() {
            match git.read(rel) {
                Ok(Some(bytes)) => return Ok(bytes),
                Ok(None) => return Err(io::ErrorKind::NotFound.into()),
                Err(err) => {
                    tracing::warn!(rel, %err, "git normalization failed; reading raw bytes");
                }
            }
        }
        std::fs::read(self.root.join(rel))
    }

    /// Like [`ContentReader::read`], as UTF-8 text.
    ///
    /// # Errors
    /// [`io::ErrorKind::InvalidData`] when the content is not UTF-8, otherwise as [`ContentReader::read`].
    pub fn read_text(&mut self, rel: &str) -> io::Result<String> {
        String::from_utf8(self.read(rel)?)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))
    }
}
