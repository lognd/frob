// frob:ticket 01M56M6YM7DZTNXT65BP75ES1Y
//! Per-command discovery scope: repositories are opened once per path while a scope is live.
//!
//! A command (`frob land`, `frob check`) that touches the same work tree from several layers
//! would otherwise re-run `gix::discover` for each. Hold a [`DiscoverScope`] for the command's
//! duration and read through [`Repo::discover_shared`]; outside a scope it is plain
//! [`Repo::discover`], so nothing is cached across commands.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

use tracing::debug;

use crate::{GitError, Repo};

/// Live scopes and the repositories opened under them, keyed by the path they were found from.
static STATE: Mutex<State> = Mutex::new(State {
    depth: 0,
    repos: None,
});

struct State {
    depth: usize,
    repos: Option<HashMap<PathBuf, Repo>>,
}

/// Guard that turns on repository sharing for [`Repo::discover_shared`] until it is dropped.
#[derive(Debug)]
#[must_use = "the scope ends when the guard is dropped"]
pub struct DiscoverScope(());

impl DiscoverScope {
    /// Start sharing discovered repositories; nested scopes share one cache.
    pub fn begin() -> Self {
        let mut st = STATE
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        st.depth += 1;
        st.repos.get_or_insert_with(HashMap::new);
        debug!(depth = st.depth, "repository discovery scope begun");
        Self(())
    }
}

impl Drop for DiscoverScope {
    /// The outermost drop forgets every shared repository.
    fn drop(&mut self) {
        let mut st = STATE
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        st.depth = st.depth.saturating_sub(1);
        if st.depth == 0 {
            st.repos = None;
        }
        debug!(depth = st.depth, "repository discovery scope ended");
    }
}

impl Repo {
    /// Like [`Repo::discover`], but reuses the handle already opened for `cwd` in the live
    /// [`DiscoverScope`]; with no scope live it is exactly [`Repo::discover`].
    ///
    /// # Errors
    /// [`GitError::Discover`] when `cwd` is not inside a repository.
    pub fn discover_shared(cwd: impl AsRef<Path>) -> Result<Self, GitError> {
        let cwd = cwd.as_ref();
        {
            let st = STATE
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            if let Some(hit) = st.repos.as_ref().and_then(|m| m.get(cwd)) {
                debug!(cwd = ?cwd, "shared repository reused");
                return Ok(hit.clone());
            }
        }
        let repo = Self::discover(cwd)?;
        let mut st = STATE
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        if let Some(m) = st.repos.as_mut() {
            m.insert(cwd.to_path_buf(), repo.clone());
        }
        Ok(repo)
    }
}
