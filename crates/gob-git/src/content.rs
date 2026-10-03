//! Worktree files read as git would store them (clean filters applied, symlinks as targets).

// frob:ticket 01M40THSWB75TFY8949M4T7MXR

use std::cell::OnceCell;
use std::path::{Path, PathBuf};

use gix::filter::plumbing::pipeline::convert::ToGitOutcome;
use tracing::{debug, trace};

use crate::read::odb_err;
use crate::{GitError, Repo};

/// A reader that converts worktree files to their git representation, reusing one filter pipeline.
///
/// Obtained from [`WorktreeSource::with_reader`] or [`Repo::with_worktree_reader`];
/// building the pipeline loads the index and attributes, so read many files per reader.
pub struct WorktreeReader<'r> {
    root: &'r Path,
    prefix: &'r str,
    workdir: &'r Path,
    repo: &'r OnceCell<gix::Repository>,
    live: Option<Live<'r>>,
}

/// The filter pipeline and index state, built on the first file that needs conversion.
struct Live<'r> {
    pipeline: gix::filter::Pipeline<'r>,
    state: gix::worktree::IndexPersistedOrInMemory,
}

impl<'r> WorktreeReader<'r> {
    /// The pipeline, building it (open, index, attributes) on first use.
    fn live(&mut self) -> Result<&mut Live<'r>, GitError> {
        if self.live.is_none() {
            self.build_live()?;
        }
        match &mut self.live {
            Some(live) => Ok(live),
            None => unreachable!("build_live fills `live` or returns an error"),
        }
    }

    /// Opens the repository and builds the filter pipeline into `self.live`.
    fn build_live(&mut self) -> Result<(), GitError> {
        let repo = if let Some(r) = self.repo.get() {
            r
        } else {
            let opened = gix::open(self.workdir).map_err(odb_err)?;
            self.repo.get_or_init(|| opened)
        };
        let (pipeline, state) = repo
            .filter_pipeline(None)
            .map_err(|e| GitError::Index(e.to_string()))?;
        self.live = Some(Live { pipeline, state });
        Ok(())
    }
}

impl WorktreeReader<'_> {
    /// The bytes git would store as the blob for `rel` (relative to the source root), or `None` when absent.
    ///
    /// A symlink yields its target path string (never the followed content); a
    /// regular file is run through the clean filters (`core.autocrlf`,
    /// `core.eol`, `.gitattributes` text/eol, configured filters).
    ///
    /// # Errors
    /// [`GitError::Io`] on unreadable files, [`GitError::Index`] when the filter pipeline fails.
    pub fn read(&mut self, rel: &str) -> Result<Option<Vec<u8>>, GitError> {
        use std::io::Read;
        let full = self.root.join(rel);
        let git_rel = if self.prefix.is_empty() {
            rel.to_owned()
        } else {
            format!("{}/{rel}", self.prefix)
        };
        let ctx = |e: std::io::Error| GitError::io(format!("reading {rel}"), e);
        let meta = match std::fs::symlink_metadata(&full) {
            Ok(m) => m,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(e) => return Err(ctx(e)),
        };
        if meta.file_type().is_symlink() {
            let target = std::fs::read_link(&full).map_err(ctx)?;
            trace!(rel, "symlink hashed as its target string");
            return Ok(Some(gix::path::into_bstr(target).into_owned().into()));
        }
        if !meta.is_file() {
            return Ok(None);
        }
        let file = std::fs::File::open(&full).map_err(ctx)?;
        let live = self.live()?;
        let outcome = live
            .pipeline
            .convert_to_git(file, Path::new(&git_rel), &live.state)
            .map_err(|e| GitError::Index(e.to_string()))?;
        let mut out = Vec::new();
        match outcome {
            ToGitOutcome::Unchanged(mut f) => f.read_to_end(&mut out).map_err(ctx)?,
            ToGitOutcome::Buffer(b) => {
                out.extend_from_slice(b);
                b.len()
            }
            ToGitOutcome::Process(mut r) => r.read_to_end(&mut out).map_err(ctx)?,
        };
        Ok(Some(out))
    }
}

/// A thread-safe handle on a worktree directory inside a git checkout; opens a fresh reader per use.
#[derive(Debug, Clone)]
pub struct WorktreeSource {
    workdir: PathBuf,
    /// Slash-separated path of the source root below the checkout root (empty when equal).
    prefix: String,
    root: PathBuf,
}

impl WorktreeSource {
    /// The source for `root` when it lies inside a non-bare git checkout; `None` otherwise.
    pub fn locate(root: &Path) -> Option<Self> {
        let repo = Repo::discover(root).ok()?;
        let workdir = std::fs::canonicalize(repo.work_dir()?).ok()?;
        let canon = std::fs::canonicalize(root).ok()?;
        let prefix = canon
            .strip_prefix(&workdir)
            .ok()?
            .components()
            .map(|c| c.as_os_str().to_string_lossy())
            .collect::<Vec<_>>()
            .join("/");
        debug!(root = %root.display(), workdir = %workdir.display(), "git-normalized content source located");
        Some(Self {
            workdir,
            prefix,
            root: canon,
        })
    }

    /// Runs `f` with a [`WorktreeReader`] over a freshly opened repository (current config and index).
    ///
    /// The repository is opened and its filters built lazily, on the first file
    /// that needs them; a failure there surfaces as that read's error.
    pub fn with_reader<T>(&self, f: impl FnOnce(&mut WorktreeReader<'_>) -> T) -> T {
        let repo = OnceCell::new();
        let mut reader = WorktreeReader {
            root: &self.root,
            prefix: &self.prefix,
            workdir: &self.workdir,
            repo: &repo,
            live: None,
        };
        f(&mut reader)
    }
}

impl Repo {
    /// Runs `f` with a [`WorktreeReader`] over this checkout.
    ///
    /// # Errors
    /// [`GitError::Unsupported`] for a bare repository.
    pub fn with_worktree_reader<T>(
        &self,
        f: impl FnOnce(&mut WorktreeReader<'_>) -> T,
    ) -> Result<T, GitError> {
        let Some(root) = self.work_dir() else {
            return Err(GitError::Unsupported(
                "bare repository has no worktree".into(),
            ));
        };
        let src = WorktreeSource {
            workdir: root.to_path_buf(),
            prefix: String::new(),
            root: root.to_path_buf(),
        };
        Ok(src.with_reader(f))
    }

    /// The bytes git would store as the blob for worktree path `rel`, or `None` when it is absent.
    ///
    /// A symlink yields its target path string (never the followed content);
    /// a regular file is run through the clean filters (`core.autocrlf`,
    /// `core.eol`, `.gitattributes` text/eol, configured filters). Use this,
    /// not raw file bytes, for any digest meant to match git's view; for many
    /// files use [`Repo::with_worktree_reader`] to share one pipeline.
    ///
    /// # Errors
    /// [`GitError::Unsupported`] for a bare repository, [`GitError::Io`] on
    /// unreadable files, [`GitError::Index`] when the filter pipeline fails.
    pub fn worktree_content_as_git(&self, rel: &str) -> Result<Option<Vec<u8>>, GitError> {
        self.with_worktree_reader(|r| r.read(rel))?
    }
}
