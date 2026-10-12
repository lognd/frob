//! Adapter that lets gob-walk read git-normalized content through gob-git.

use std::path::Path;
use std::sync::Arc;

use gob_walk::{BackendError, ContentBackend, ContentLocator, FileReader};
use tracing::debug;

use crate::{WorktreeReader, WorktreeSource};

/// The gob-walk content backend: git-normalized reads inside a checkout.
#[derive(Debug, Clone, Copy, Default)]
pub struct GitContentBackend;

impl ContentBackend for GitContentBackend {
    fn locate(&self, root: &Path) -> Option<Arc<dyn ContentLocator>> {
        WorktreeSource::locate(root).map(|s| Arc::new(s) as Arc<dyn ContentLocator>)
    }
}

impl ContentLocator for WorktreeSource {
    fn with_reader(&self, f: &mut dyn FnMut(&mut dyn FileReader)) {
        WorktreeSource::with_reader(self, |r| f(r));
    }
}

impl FileReader for WorktreeReader<'_> {
    fn read(&mut self, rel: &str) -> Result<Option<Vec<u8>>, BackendError> {
        WorktreeReader::read(self, rel).map_err(Into::into)
    }
}

/// Installs [`GitContentBackend`] as gob-walk's process-wide content backend; call once at startup.
pub fn install_content_backend() {
    let fresh = gob_walk::install_backend(Arc::new(GitContentBackend));
    debug!(fresh, "git content backend installed");
}
