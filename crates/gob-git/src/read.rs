//! Repository discovery and the gix-backed read APIs.

use std::path::{Path, PathBuf};
use std::sync::Arc;

use gix::bstr::ByteSlice;
use gob_exec::{Limits, Runner};
use tracing::{debug, info};

use crate::{GitError, Oid};

/// Where `HEAD` points.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Head {
    /// Short branch name, or `None` when detached.
    pub branch: Option<String>,
    /// The commit `HEAD` resolves to, or `None` on an unborn branch.
    pub oid: Option<Oid>,
}

/// One entry of [`Repo::list_worktrees`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorktreeInfo {
    /// Worktree root directory.
    pub path: PathBuf,
    /// Short branch name checked out there, or `None` when detached or unborn.
    pub branch: Option<String>,
}

/// An open repository: one `gix` handle plus the runner used for spawn fallbacks.
pub struct Repo {
    pub(crate) gix: gix::Repository,
    pub(crate) runner: Arc<Runner>,
}

impl std::fmt::Debug for Repo {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Repo")
            .field("git_dir", &self.gix.git_dir())
            .finish_non_exhaustive()
    }
}

pub(crate) fn rev_err(spec: &str, e: impl std::fmt::Display) -> GitError {
    GitError::Rev {
        spec: spec.to_owned(),
        detail: e.to_string(),
    }
}

pub(crate) fn odb_err(e: impl std::fmt::Display) -> GitError {
    GitError::Odb(e.to_string())
}

impl Repo {
    /// Open the repository containing `cwd`, including from a linked worktree.
    ///
    /// # Errors
    /// [`GitError::Discover`] when `cwd` is not inside a repository.
    pub fn discover(cwd: impl AsRef<Path>) -> Result<Self, GitError> {
        let cwd = cwd.as_ref();
        let gix = gix::discover(cwd).map_err(|e| GitError::Discover {
            path: cwd.to_path_buf(),
            detail: e.to_string(),
        })?;
        debug!(git_dir = %gix.git_dir().display(), "repository discovered");
        Ok(Self::from_gix(gix))
    }

    /// Initialise a new non-bare repository at `path` and open it.
    ///
    /// # Errors
    /// [`GitError::Odb`] when git refuses to initialise the directory.
    pub fn init(path: impl AsRef<Path>) -> Result<Self, GitError> {
        let gix = gix::init(path.as_ref()).map_err(odb_err)?;
        info!(path = %path.as_ref().display(), "repository initialised");
        Ok(Self::from_gix(gix))
    }

    fn from_gix(gix: gix::Repository) -> Self {
        Self {
            gix,
            runner: Arc::new(Runner::new(Limits::default())),
        }
    }

    /// Open a handle with its own index cache.
    ///
    /// gix shares one index snapshot across clones and revalidates it by index
    /// mtime alone, so rapid successive index rewrites (as `commit_paths`
    /// does) can leave it stale; index readers must not use the shared one.
    pub(crate) fn fresh_gix(&self) -> Result<gix::Repository, GitError> {
        let path = self.gix.workdir().unwrap_or_else(|| self.gix.git_dir());
        gix::open(path).map_err(odb_err)
    }

    /// Use `runner` (shared with the rest of the process) for spawn fallbacks.
    #[must_use]
    pub fn with_runner(mut self, runner: Arc<Runner>) -> Self {
        self.runner = runner;
        self
    }

    /// The runner spawn fallbacks go through.
    pub fn runner(&self) -> &Runner {
        &self.runner
    }

    /// The worktree root of this checkout; `None` for a bare repository.
    pub fn work_dir(&self) -> Option<&Path> {
        self.gix.workdir()
    }

    /// The git dir of this checkout (`.git`, or `.git/worktrees/<id>` when linked).
    pub fn git_dir(&self) -> &Path {
        self.gix.git_dir()
    }

    /// The common git dir shared by all worktrees.
    pub fn common_dir(&self) -> &Path {
        self.gix.common_dir()
    }

    /// True when this checkout is a linked worktree rather than the main one.
    pub fn is_linked_worktree(&self) -> bool {
        self.gix.git_dir() != self.gix.common_dir()
    }

    /// Where `HEAD` points.
    ///
    /// # Errors
    /// [`GitError::Ref`] when `HEAD` cannot be read.
    pub fn head(&self) -> Result<Head, GitError> {
        let head = self.gix.head().map_err(|e| GitError::Ref(e.to_string()))?;
        let branch = head
            .referent_name()
            .map(|n| n.shorten().to_str_lossy().into_owned());
        let oid = head.id().map(gix::Id::detach);
        Ok(Head { branch, oid })
    }

    /// The short name of the checked-out branch, or `None` when detached.
    ///
    /// # Errors
    /// [`GitError::Ref`] when `HEAD` cannot be read.
    pub fn current_branch(&self) -> Result<Option<String>, GitError> {
        Ok(self.head()?.branch)
    }

    /// Resolve `spec` (ref, oid, `rev^`, ...) to a commit or object id.
    ///
    /// # Errors
    /// [`GitError::Rev`] when the spec does not resolve.
    pub fn rev_parse(&self, spec: &str) -> Result<Oid, GitError> {
        let id = self
            .gix
            .rev_parse_single(spec)
            .map_err(|e| rev_err(spec, e))?;
        Ok(id.detach())
    }

    /// The best common ancestor of `a` and `b`, or `None` when unrelated.
    ///
    /// # Errors
    /// [`GitError::Rev`] when either spec does not resolve.
    pub fn merge_base(&self, a: &str, b: &str) -> Result<Option<Oid>, GitError> {
        let (ia, ib) = (self.rev_parse(a)?, self.rev_parse(b)?);
        match self.gix.merge_base(ia, ib) {
            Ok(id) => Ok(Some(id.detach())),
            Err(gix::repository::merge_base::Error::NotFound { .. }) => Ok(None),
            Err(e) => Err(rev_err(&format!("{a}...{b}"), e)),
        }
    }

    /// The contents of `path` at `rev`, or `None` when absent there.
    ///
    /// # Errors
    /// [`GitError::Rev`] when `rev` does not resolve; [`GitError::Odb`] on read failure.
    pub fn read_blob_at(&self, rev: &str, path: &str) -> Result<Option<Vec<u8>>, GitError> {
        let tree = self.tree_of(&self.rev_parse(rev)?)?;
        let entry = tree.lookup_entry_by_path(path).map_err(odb_err)?;
        let Some(entry) = entry else { return Ok(None) };
        if !entry.mode().is_blob() {
            return Ok(None);
        }
        let blob = self.gix.find_blob(entry.object_id()).map_err(odb_err)?;
        Ok(Some(blob.data.clone()))
    }

    /// Peel a commit, tag or tree id to its tree.
    pub(crate) fn tree_of(&self, id: &Oid) -> Result<gix::Tree<'_>, GitError> {
        let obj = self.gix.find_object(*id).map_err(odb_err)?;
        obj.peel_to_tree().map_err(odb_err)
    }

    /// Every worktree (main first), with its checked-out branch.
    ///
    /// # Errors
    /// [`GitError::Io`] when the worktree list cannot be read.
    pub fn list_worktrees(&self) -> Result<Vec<WorktreeInfo>, GitError> {
        let info_of = |repo: &gix::Repository, path: PathBuf| WorktreeInfo {
            path,
            branch: repo.head().ok().and_then(|h| {
                h.referent_name()
                    .map(|n| n.shorten().to_str_lossy().into_owned())
            }),
        };
        let mut out = Vec::new();
        let main = self
            .gix
            .main_repo()
            .map_err(|e| GitError::Odb(e.to_string()))?;
        if let Some(w) = main.workdir() {
            out.push(info_of(&main, w.to_path_buf()));
        }
        for proxy in self
            .gix
            .worktrees()
            .map_err(|e| GitError::io("listing worktrees", e))?
        {
            let Ok(base) = proxy.base() else { continue };
            let Ok(repo) = proxy.into_repo_with_possibly_inaccessible_worktree() else {
                continue;
            };
            out.push(info_of(&repo, base));
        }
        debug!(count = out.len(), "worktrees listed");
        Ok(out)
    }

    /// `user.name` and `user.email` from git config, when both are set.
    pub fn config_user(&self) -> Option<(String, String)> {
        let cfg = self.gix.config_snapshot();
        let name = cfg.string("user.name")?.to_str_lossy().into_owned();
        let email = cfg.string("user.email")?.to_str_lossy().into_owned();
        Some((name, email))
    }
}
