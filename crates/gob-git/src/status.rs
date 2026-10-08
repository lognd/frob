//! Status and path diffs over gix: tree vs tree, tree vs index, tree vs worktree.

use std::collections::BTreeMap;

use gix::bstr::ByteSlice;
use gix::object::tree::diff::ChangeDetached;
use gix::status::UntrackedFiles;
use tracing::{debug, trace};

use crate::read::odb_err;
use crate::{GitError, Oid, Repo};

/// How a path changed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ChangeKind {
    /// Present only on the new side.
    Added,
    /// Present on both sides with different content or mode.
    Modified,
    /// Present only on the old side.
    Deleted,
}

/// A path that differs between two [`TreeRef`]s.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ChangedPath {
    /// Repo-relative, slash-separated path.
    pub path: String,
    /// How it changed from the old side to the new side.
    pub kind: ChangeKind,
}

/// One side of a [`Repo::diff_names`] comparison.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TreeRef {
    /// The tree of `HEAD`.
    Head,
    /// The tree of a named ref or any rev spec.
    Ref(String),
    /// The tree of a commit, tag or tree object id.
    Oid(Oid),
    /// The files on disk (tracked changes and untracked, ignores honoured); new side only.
    WorkTree,
    /// The staged index; new side only.
    Index,
}

/// What a status entry reports.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StatusKind {
    /// New to the index (staged) or tracked via intent-to-add.
    Added,
    /// Content or mode changed.
    Modified,
    /// Removed from the index or the disk.
    Deleted,
    /// On disk, not tracked and not ignored.
    Untracked,
    /// Moved from another path (staged side only).
    Renamed,
}

/// Options for [`Repo::status`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct StatusOptions {
    /// Include untracked files (never ignored ones).
    pub include_untracked: bool,
}

impl Default for StatusOptions {
    fn default() -> Self {
        Self {
            include_untracked: true,
        }
    }
}

/// One changed path from [`Repo::status`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StatusEntry {
    /// Repo-relative, slash-separated path.
    pub path: String,
    /// What changed.
    pub kind: StatusKind,
    /// True when the change is staged (`HEAD` vs index), false when it is on disk only.
    pub staged: bool,
}

type TreeMap = BTreeMap<String, (Oid, bool)>;

impl Repo {
    /// Changed and untracked paths of this checkout, honouring ignores.
    ///
    /// # Errors
    /// [`GitError::Status`] when gix cannot compute the status.
    pub fn status(&self, opts: &StatusOptions) -> Result<Vec<StatusEntry>, GitError> {
        let st_err = |e: &dyn std::fmt::Display| GitError::Status(e.to_string());
        let untracked = if opts.include_untracked {
            UntrackedFiles::Files
        } else {
            UntrackedFiles::None
        };
        let fresh = self.fresh_gix()?;
        let platform = fresh
            .status(gix::progress::Discard)
            .map_err(|e| st_err(&e))?
            .untracked_files(untracked);
        let iter = platform.into_iter(Vec::new()).map_err(|e| st_err(&e))?;
        let mut out = Vec::new();
        for item in iter {
            let item = item.map_err(|e| st_err(&e))?;
            if let Some(e) = status_entry(&item) {
                trace!(path = %e.path, kind = ?e.kind, staged = e.staged, "status entry");
                out.push(e);
            }
        }
        out.sort_by(|a, b| a.path.cmp(&b.path).then(a.staged.cmp(&b.staged)));
        debug!(count = out.len(), "status computed");
        Ok(out)
    }

    /// Every file (blob) path tracked by the tree of `rev`, sorted; the denominator for "does this scope glob match anything".
    ///
    /// # Errors
    /// [`GitError::Rev`] when `rev` does not resolve; [`GitError::Odb`] on read failure.
    pub fn tracked_files_at(&self, rev: &str) -> Result<Vec<String>, GitError> {
        let tree = self.tree_of(&self.rev_parse(rev)?)?;
        let files: Vec<String> = Self::flatten_tree(&tree)?.into_keys().collect();
        debug!(rev, count = files.len(), "tracked files listed");
        Ok(files)
    }

    /// Paths that differ going from `from` to `to`, sorted by path.
    ///
    /// Supported: tree-like `from` (`Head`, `Ref`, `Oid`) against any `to`.
    /// Against `WorkTree` a tracked path is reported only when its disk
    /// content really differs from the tree, and untracked files count as added.
    ///
    /// # Errors
    /// [`GitError::Unsupported`] for `WorkTree` or `Index` as `from`; other
    /// variants for unresolvable refs or unreadable objects.
    pub fn diff_names(&self, from: &TreeRef, to: &TreeRef) -> Result<Vec<ChangedPath>, GitError> {
        let old = self.tree_for(from)?.ok_or_else(|| {
            GitError::Unsupported(format!("{from:?} is only valid as the new side"))
        })?;
        let mut out = match to {
            TreeRef::Index => diff_maps(&Self::flatten_tree(&old)?, &self.index_map()?),
            TreeRef::WorkTree => self.diff_to_worktree(&old)?,
            other => {
                let new = self
                    .tree_for(other)?
                    .ok_or_else(|| GitError::Unsupported(format!("{other:?} has no tree")))?;
                self.diff_trees(&old, &new)?
            }
        };
        out.sort_by(|a, b| a.path.cmp(&b.path));
        debug!(count = out.len(), ?from, ?to, "diff_names computed");
        Ok(out)
    }

    fn tree_for(&self, r: &TreeRef) -> Result<Option<gix::Tree<'_>>, GitError> {
        let id = match r {
            TreeRef::Head => self.rev_parse("HEAD")?,
            TreeRef::Ref(s) => self.rev_parse(s)?,
            TreeRef::Oid(o) => *o,
            TreeRef::WorkTree | TreeRef::Index => return Ok(None),
        };
        self.tree_of(&id).map(Some)
    }

    fn diff_trees(
        &self,
        old: &gix::Tree<'_>,
        new: &gix::Tree<'_>,
    ) -> Result<Vec<ChangedPath>, GitError> {
        let mut opts = gix::diff::Options::default();
        opts.track_rewrites(None);
        let changes = self
            .gix
            .diff_tree_to_tree(old, new, opts)
            .map_err(|e| GitError::Status(e.to_string()))?;
        let mut out = Vec::new();
        for c in changes {
            let (loc, kind) = match &c {
                ChangeDetached::Addition {
                    location,
                    entry_mode,
                    ..
                } => (
                    location,
                    (!entry_mode.is_tree()).then_some(ChangeKind::Added),
                ),
                ChangeDetached::Deletion {
                    location,
                    entry_mode,
                    ..
                } => (
                    location,
                    (!entry_mode.is_tree()).then_some(ChangeKind::Deleted),
                ),
                ChangeDetached::Modification {
                    location,
                    entry_mode,
                    ..
                } => (
                    location,
                    (!entry_mode.is_tree()).then_some(ChangeKind::Modified),
                ),
                ChangeDetached::Rewrite { location, .. } => (location, Some(ChangeKind::Modified)),
            };
            if let Some(kind) = kind {
                out.push(ChangedPath {
                    path: loc.to_str_lossy().into_owned(),
                    kind,
                });
            }
        }
        Ok(out)
    }

    pub(crate) fn flatten_tree(tree: &gix::Tree<'_>) -> Result<TreeMap, GitError> {
        let mut rec = gix::traverse::tree::Recorder::default();
        tree.traverse().breadthfirst(&mut rec).map_err(odb_err)?;
        Ok(rec
            .records
            .into_iter()
            .filter(|e| e.mode.is_blob())
            .map(|e| {
                (
                    e.filepath.to_str_lossy().into_owned(),
                    (
                        e.oid,
                        e.mode.kind() == gix::object::tree::EntryKind::BlobExecutable,
                    ),
                )
            })
            .collect())
    }

    fn index_map(&self) -> Result<TreeMap, GitError> {
        let index = self
            .fresh_gix()?
            .index_or_empty()
            .map_err(|e| GitError::Index(e.to_string()))?;
        Ok(index
            .entries()
            .iter()
            .filter(|e| e.stage_raw() == 0)
            .map(|e| {
                (
                    e.path(&index).to_str_lossy().into_owned(),
                    (e.id, e.mode == gix::index::entry::Mode::FILE_EXECUTABLE),
                )
            })
            .collect())
    }

    /// Tree-to-worktree names computed by gix's own status machinery with `old` as the base tree.
    ///
    /// Symlinks are compared by target string, and `core.autocrlf` / attribute
    /// filters apply exactly as in `git status`, so no path git would not
    /// report is reported. Each candidate path is classified by whether it exists
    /// in `old` and whether it exists on disk (renames are not tracked).
    fn diff_to_worktree(&self, old: &gix::Tree<'_>) -> Result<Vec<ChangedPath>, GitError> {
        use gix::status::index_worktree::Item as W;
        use gix::status::plumbing::index_as_worktree::{Change, EntryStatus};
        let st_err = |e: &dyn std::fmt::Display| GitError::Status(e.to_string());
        if self.work_dir().is_none() {
            return Err(GitError::Unsupported(
                "bare repository has no worktree".into(),
            ));
        }
        let fresh = self.fresh_gix()?;
        let platform = fresh
            .status(gix::progress::Discard)
            .map_err(|e| st_err(&e))?
            .head_tree(old.id)
            .untracked_files(UntrackedFiles::Files)
            .index_worktree_rewrites(None)
            .tree_index_track_renames(gix::status::tree_index::TrackRenames::Disabled);
        let iter = platform.into_iter(Vec::new()).map_err(|e| st_err(&e))?;
        // path -> exists on disk now (last writer wins: the worktree side is authoritative).
        let mut disk: BTreeMap<String, bool> = BTreeMap::new();
        for item in iter {
            let item = item.map_err(|e| st_err(&e))?;
            match &item {
                gix::status::Item::TreeIndex(change) => {
                    use gix::diff::index::Change as C;
                    let (loc, present) = match change {
                        C::Deletion { location, .. } => (location, false),
                        C::Addition { location, .. }
                        | C::Modification { location, .. }
                        | C::Rewrite { location, .. } => (location, true),
                    };
                    disk.entry(loc.to_str_lossy().into_owned())
                        .or_insert(present);
                }
                gix::status::Item::IndexWorktree(W::Modification {
                    rela_path, status, ..
                }) => {
                    let present = match status {
                        EntryStatus::Change(Change::Removed) => false,
                        EntryStatus::NeedsUpdate(_) => continue,
                        _ => true,
                    };
                    disk.insert(rela_path.to_str_lossy().into_owned(), present);
                }
                gix::status::Item::IndexWorktree(W::DirectoryContents { entry, .. }) => {
                    if entry.status == gix::dir::entry::Status::Untracked {
                        disk.insert(entry.rela_path.to_str_lossy().into_owned(), true);
                    }
                }
                gix::status::Item::IndexWorktree(W::Rewrite { dirwalk_entry, .. }) => {
                    disk.insert(dirwalk_entry.rela_path.to_str_lossy().into_owned(), true);
                }
            }
        }
        let mut out = Vec::new();
        for (path, on_disk) in disk {
            let in_old = old
                .lookup_entry_by_path(&path)
                .map_err(odb_err)?
                .is_some_and(|e| !e.mode().is_tree());
            let kind = match (in_old, on_disk) {
                (false, false) => None,
                (false, true) => Some(ChangeKind::Added),
                (true, false) => Some(ChangeKind::Deleted),
                (true, true) => Some(ChangeKind::Modified),
            };
            trace!(%path, in_old, on_disk, ?kind, "worktree candidate classified");
            if let Some(kind) = kind {
                out.push(ChangedPath { path, kind });
            }
        }
        Ok(out)
    }
}

fn diff_maps(old: &TreeMap, new: &TreeMap) -> Vec<ChangedPath> {
    let mut out = Vec::new();
    for (p, v) in old {
        match new.get(p) {
            None => out.push(ChangedPath {
                path: p.clone(),
                kind: ChangeKind::Deleted,
            }),
            Some(n) if n != v => out.push(ChangedPath {
                path: p.clone(),
                kind: ChangeKind::Modified,
            }),
            Some(_) => {}
        }
    }
    for p in new.keys().filter(|p| !old.contains_key(*p)) {
        out.push(ChangedPath {
            path: p.clone(),
            kind: ChangeKind::Added,
        });
    }
    out
}

fn status_entry(item: &gix::status::Item) -> Option<StatusEntry> {
    use gix::status::index_worktree::Item as W;
    match item {
        gix::status::Item::TreeIndex(change) => {
            use gix::diff::index::Change as C;
            let (path, kind) = match change {
                C::Addition { location, .. } => (location, StatusKind::Added),
                C::Deletion { location, .. } => (location, StatusKind::Deleted),
                C::Modification { location, .. } => (location, StatusKind::Modified),
                C::Rewrite { location, .. } => (location, StatusKind::Renamed),
            };
            Some(StatusEntry {
                path: path.to_str_lossy().into_owned(),
                kind,
                staged: true,
            })
        }
        gix::status::Item::IndexWorktree(W::Modification {
            rela_path, status, ..
        }) => {
            use gix::status::plumbing::index_as_worktree::{Change, EntryStatus};
            let kind = match status {
                EntryStatus::Change(Change::Removed) => StatusKind::Deleted,
                EntryStatus::Conflict { .. } | EntryStatus::Change(_) => StatusKind::Modified,
                EntryStatus::IntentToAdd => StatusKind::Added,
                EntryStatus::NeedsUpdate(_) => return None,
            };
            Some(StatusEntry {
                path: rela_path.to_str_lossy().into_owned(),
                kind,
                staged: false,
            })
        }
        gix::status::Item::IndexWorktree(W::DirectoryContents { entry, .. }) => {
            (entry.status == gix::dir::entry::Status::Untracked).then(|| StatusEntry {
                path: entry.rela_path.to_str_lossy().into_owned(),
                kind: StatusKind::Untracked,
                staged: false,
            })
        }
        gix::status::Item::IndexWorktree(W::Rewrite { dirwalk_entry, .. }) => Some(StatusEntry {
            path: dirwalk_entry.rela_path.to_str_lossy().into_owned(),
            kind: StatusKind::Renamed,
            staged: false,
        }),
    }
}
