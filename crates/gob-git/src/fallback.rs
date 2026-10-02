//! The only spawns gob-git makes: `worktree add`, `merge`, `push`, via gob-exec.

use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_exec::{Outcome, Program, Spec};
use tracing::{debug, info, warn};

use crate::{GitError, Repo, SpawnClass};

/// The result of [`Repo::merge_branch`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MergeOutcome {
    /// The branch is already contained in the worktree's `HEAD`; nothing ran.
    UpToDate,
    /// `HEAD` moved forward to the branch tip.
    FastForward,
    /// A merge commit was created.
    Merged,
    /// The merge stopped with these conflicted paths left in the index.
    Conflicts(Vec<String>),
}

const TIMEOUT: Duration = Duration::from_secs(300);

impl Repo {
    fn run_git(
        &self,
        class: SpawnClass,
        cwd: &Path,
        args: &[&str],
    ) -> Result<(i32, String), GitError> {
        debug_assert!(class.is_git());
        let spec = Spec {
            program: Program::Git,
            args: args.iter().map(|s| (*s).to_owned()).collect(),
            cwd: Some(cwd.to_path_buf()),
            env: Vec::new(),
            timeout: TIMEOUT,
            capture: true,
        };
        let joined = args.join(" ");
        info!(class = class.label(), args = %joined, "spawn fallback");
        let out = self.runner.run(&spec).map_err(|e| GitError::Spawn {
            args: joined.clone(),
            detail: e.to_string(),
        })?;
        match out.status {
            Outcome::Exited(code) => Ok((code, format!("{}{}", out.stdout, out.stderr))),
            other => Err(GitError::Spawn {
                args: joined,
                detail: format!("{other:?}: {}", out.stderr),
            }),
        }
    }

    /// Create a linked worktree at `path` on `branch`, creating the branch from `start_point` when it does not exist.
    ///
    /// Spawns `git worktree add` (class [`SpawnClass::GitWorktreeAdd`]) because
    /// gix 0.87 has no worktree-add write path.
    ///
    /// # Errors
    /// [`GitError::Spawn`] when git is missing or exits non-zero.
    pub fn worktree_add(
        &self,
        path: &Path,
        branch: &str,
        start_point: &str,
    ) -> Result<(), GitError> {
        let cwd = self.work_dir().unwrap_or_else(|| self.git_dir());
        let p = path.to_string_lossy();
        let exists = self
            .gix
            .try_find_reference(&format!("refs/heads/{branch}"))
            .map_err(|e| GitError::Ref(e.to_string()))?
            .is_some();
        let args: Vec<&str> = if exists {
            vec!["worktree", "add", &p, branch]
        } else {
            vec!["worktree", "add", "-b", branch, &p, start_point]
        };
        let (code, text) = self.run_git(SpawnClass::GitWorktreeAdd, cwd, &args)?;
        if code == 0 {
            Ok(())
        } else {
            Err(GitError::Spawn {
                args: args.join(" "),
                detail: text,
            })
        }
    }

    /// Merge `branch` into the checkout at `into_worktree`.
    ///
    /// Containment is decided in-process with gix (no spawn when already
    /// merged). Applying a merge to a worktree and index is outside gix's
    /// write path, so the merge itself is one `git merge --no-edit` spawn
    /// (class [`SpawnClass::GitMerge`]); conflicted paths are then read from the
    /// index stages without a second spawn and the conflicted state is left for the caller.
    ///
    /// # Errors
    /// [`GitError::Spawn`] when git is missing or fails for a reason other than conflicts.
    pub fn merge_branch(
        &self,
        into_worktree: &Path,
        branch: &str,
    ) -> Result<MergeOutcome, GitError> {
        let target = Repo::discover(into_worktree)?;
        let head = target
            .head()?
            .oid
            .ok_or_else(|| GitError::Unsupported("cannot merge into an unborn branch".into()))?;
        let theirs = target.rev_parse(branch)?;
        let base = target
            .gix
            .merge_base(head, theirs)
            .ok()
            .map(gix::Id::detach);
        if base == Some(theirs) {
            debug!(branch, "already up to date");
            return Ok(MergeOutcome::UpToDate);
        }
        let ff = base == Some(head);
        let (code, text) = self.run_git(
            SpawnClass::GitMerge,
            into_worktree,
            &["merge", "--no-edit", branch],
        )?;
        if code == 0 {
            return Ok(if ff {
                MergeOutcome::FastForward
            } else {
                MergeOutcome::Merged
            });
        }
        let conflicts = Repo::discover(into_worktree)?.conflicted_paths()?;
        if conflicts.is_empty() {
            return Err(GitError::Spawn {
                args: format!("merge --no-edit {branch}"),
                detail: text,
            });
        }
        warn!(branch, count = conflicts.len(), "merge left conflicts");
        Ok(MergeOutcome::Conflicts(conflicts))
    }

    /// Paths with unmerged (stage > 0) index entries.
    fn conflicted_paths(&self) -> Result<Vec<String>, GitError> {
        use gix::bstr::ByteSlice;
        let index = self
            .gix
            .open_index()
            .map_err(|e| GitError::Index(e.to_string()))?;
        let mut v: Vec<String> = index
            .entries()
            .iter()
            .filter(|e| e.stage_raw() != 0)
            .map(|e| e.path(&index).to_str_lossy().into_owned())
            .collect();
        v.dedup();
        Ok(v)
    }

    /// Push `refspec` to `remote`.
    ///
    /// Spawns `git push` (class [`SpawnClass::GitPush`]); gix has no push transport.
    ///
    /// # Errors
    /// [`GitError::Spawn`] when git is missing or the push is rejected.
    pub fn push(&self, remote: &str, refspec: &str) -> Result<(), GitError> {
        let cwd: PathBuf = self
            .work_dir()
            .unwrap_or_else(|| self.git_dir())
            .to_path_buf();
        let (code, text) = self.run_git(SpawnClass::GitPush, &cwd, &["push", remote, refspec])?;
        if code == 0 {
            Ok(())
        } else {
            Err(GitError::Spawn {
                args: format!("push {remote} {refspec}"),
                detail: text,
            })
        }
    }
}
