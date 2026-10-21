//! File content as git would store it, so digests ignore checkout line-ending rewrites.

// frob:ticket 01M40THSWB75TFY8949M4T7MXR

use std::io;
use std::path::{Path, PathBuf};
use std::sync::{Arc, OnceLock};

/// Error type of a [`FileReader`]; opaque so the backend crate owns its error vocabulary.
pub type BackendError = Box<dyn std::error::Error + Send + Sync>;

/// Reads file content in a backend's normal form (for git: as the blob would be stored).
pub trait FileReader {
    /// The content of `rel` below the source root, or `None` when absent.
    ///
    /// # Errors
    /// A [`BackendError`] when the backend cannot produce the content.
    fn read(&mut self, rel: &str) -> Result<Option<Vec<u8>>, BackendError>;
}

/// A located, thread-safe handle that lends [`FileReader`]s for one root.
pub trait ContentLocator: Send + Sync + std::fmt::Debug {
    /// Runs `f` with a reader; the reader lives only for the call.
    fn with_reader(&self, f: &mut dyn FnMut(&mut dyn FileReader));
}

/// Finds a [`ContentLocator`] for a root; implemented by gob-git and injected by the binaries.
pub trait ContentBackend: Send + Sync {
    /// The locator for `root`, or `None` when this backend does not cover it.
    fn locate(&self, root: &Path) -> Option<Arc<dyn ContentLocator>>;
}

static BACKEND: OnceLock<Arc<dyn ContentBackend>> = OnceLock::new();

/// Installs the process-wide content backend; returns false (and keeps the first) when one is set.
pub fn install_backend(backend: Arc<dyn ContentBackend>) -> bool {
    let fresh = BACKEND.set(backend).is_ok();
    tracing::debug!(fresh, "content backend install");
    fresh
}

/// Where file content is read from: git-normalized inside a checkout, raw bytes elsewhere.
#[derive(Debug, Clone)]
pub struct ContentSource {
    root: PathBuf,
    git: Option<Arc<dyn ContentLocator>>,
}

/// Reads files of one [`ContentSource`]; reuses one filter pipeline across reads.
pub struct ContentReader<'a, 'r> {
    root: &'a Path,
    git: Option<&'a mut (dyn FileReader + 'r)>,
}

impl ContentSource {
    /// The source for `root`: git-normalized when `root` is inside a git checkout, raw otherwise.
    pub fn locate(root: &Path) -> Self {
        let git = BACKEND.get().and_then(|b| b.locate(root));
        tracing::debug!(root = ?root, git = git.is_some(), "content source located");
        Self {
            root: root.to_path_buf(),
            git,
        }
    }

    /// A source reading through an injected `locator` for `root`, bypassing the process-wide backend.
    pub fn with_locator(root: &Path, locator: Arc<dyn ContentLocator>) -> Self {
        tracing::debug!(root = ?root, "content source from injected locator");
        Self {
            root: root.to_path_buf(),
            git: Some(locator),
        }
    }

    /// Runs `f` with a reader; a repository that cannot be opened degrades to raw reads with a warning.
    ///
    /// # Panics
    /// When a [`ContentLocator`] breaks its contract of calling the closure exactly once.
    pub fn with_reader<T>(&self, f: impl FnOnce(&mut ContentReader<'_, '_>) -> T) -> T {
        if let Some(git) = &self.git {
            let mut f = Some(f);
            let mut out = None;
            git.with_reader(&mut |r| {
                let f = f.take().expect("locator calls the closure once");
                out = Some(f(&mut ContentReader {
                    root: &self.root,
                    git: Some(r),
                }));
            });
            return out.expect("locator calls the closure once");
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
        if let Some(git) = self.git.as_mut() {
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
