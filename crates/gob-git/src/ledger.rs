//! The ledger write primitive: commit a set of paths onto a ref by compare-and-swap.

use std::path::Path;

use gix::bstr::{BString, ByteSlice};
use gix::object::tree::EntryKind;
use gix::refs::Target;
use gix::refs::transaction::{Change, LogChange, PreviousValue, RefEdit, RefLog};
use tracing::{debug, info, warn};

use crate::read::odb_err;
use crate::{GitError, Oid, RelPath, Repo};

/// Tuning for [`Repo::commit_paths`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommitOptions {
    /// Retries after a lost compare-and-swap (`[tickets] cas_retries`); attempts = retries + 1.
    pub cas_retries: u32,
    /// `(name, email)` for author and committer; git config is used when `None`.
    pub author: Option<(String, String)>,
}

impl Default for CommitOptions {
    fn default() -> Self {
        Self {
            cas_retries: 5,
            author: None,
        }
    }
}

/// The result of a successful [`Repo::commit_paths`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommitOutcome {
    /// The ref's new tip (the existing tip when the changes were a no-op).
    pub oid: Oid,
    /// How many compare-and-swap attempts were lost before this one won.
    pub retries: u32,
    /// Other checkouts of the ref that were left stale because of local edits.
    pub unsynced: Vec<UnsyncedCheckout>,
}

/// A checkout of the updated ref that could not be synced to the new tip.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnsyncedCheckout {
    /// Worktree root of the skipped checkout.
    pub path: std::path::PathBuf,
    /// Changed paths whose local edits blocked the sync (they were left untouched).
    pub paths_with_local_edits: Vec<String>,
}

/// One planned change: blob id and bytes, or deletion.
struct Planned<'a> {
    path: &'a RelPath,
    blob: Option<(Oid, &'a [u8])>,
}

impl Repo {
    /// Commit `changes` (`None` deletes) onto `ref_name` without touching any index.
    ///
    /// See [`Self::commit_paths_with`], which this calls with a no-op hook.
    ///
    /// # Errors
    /// See [`Self::commit_paths_with`].
    pub fn commit_paths(
        &self,
        ref_name: &str,
        changes: &[(RelPath, Option<Vec<u8>>)],
        message: &str,
        opts: &CommitOptions,
    ) -> Result<CommitOutcome, GitError> {
        self.commit_paths_with(ref_name, changes, message, opts, &mut |_| {})
    }

    /// [`Self::commit_paths`] with `before_cas(attempt)` invoked just before each
    /// compare-and-swap; tests use it to force ref churn.
    ///
    /// The new tree is the ref tip's tree plus `changes` (a missing ref gets a
    /// root commit). The ref moves only if it still equals the tip that was read;
    /// otherwise the tip is re-read and the changes re-applied, up to
    /// `opts.cas_retries` times. When `HEAD` of this checkout is symbolic to
    /// `ref_name`, the index entries and worktree files for exactly the
    /// changed paths are then updated (via gix index editing; no `git` spawn).
    /// Every other worktree with `ref_name` checked out is synced the same way
    /// under its own `index.lock`; those blocked by local edits are reported in
    /// [`CommitOutcome::unsynced`] and the commit stands.
    ///
    /// # Errors
    /// [`GitError::CasExhausted`] when every attempt lost the race,
    /// [`GitError::LocalEdits`] when a checked-out path has uncommitted edits,
    /// [`GitError::NoIdentity`] when no author is available, plus object, ref,
    /// index and I/O failures.
    pub fn commit_paths_with(
        &self,
        ref_name: &str,
        changes: &[(RelPath, Option<Vec<u8>>)],
        message: &str,
        opts: &CommitOptions,
        before_cas: &mut dyn FnMut(u32),
    ) -> Result<CommitOutcome, GitError> {
        let full = full_ref_name(ref_name);
        let (name, email) = opts
            .author
            .clone()
            .or_else(|| self.config_user())
            .ok_or(GitError::NoIdentity)?;
        let sig = gix::actor::Signature {
            name: name.into(),
            email: email.into(),
            time: gix::date::Time::now_utc(),
        };
        let planned = self.plan(changes)?;
        let checked_out = self.is_checked_out(&full)?;
        let attempts = opts.cas_retries.saturating_add(1);
        let mut retries = 0;
        for attempt in 0..attempts {
            let tip = self.read_ref(&full)?;
            debug!(ref_name = %full, attempt, tip = ?tip, "cas attempt");
            let base_tree = match tip {
                Some(t) => self.tree_of(&t)?.id,
                None => Oid::empty_tree(self.gix.object_hash()),
            };
            if checked_out && attempt == 0 {
                let blocked = self.check_local_edits(&planned, base_tree)?;
                if let Some(path) = blocked.into_iter().next() {
                    return Err(GitError::LocalEdits { path });
                }
            }
            let new_tree = self.build_tree(base_tree, &planned)?;
            if new_tree == base_tree
                && let Some(t) = tip
            {
                info!(ref_name = %full, tip = %t, "no tree change; ledger commit skipped");
                return Ok(CommitOutcome {
                    oid: t,
                    retries,
                    unsynced: Vec::new(),
                });
            }
            let commit = gix::objs::Commit {
                tree: new_tree,
                parents: tip.into_iter().collect(),
                author: sig.clone(),
                committer: sig.clone(),
                encoding: None,
                message: message.into(),
                extra_headers: Vec::new(),
            };
            let new_id = self.gix.write_object(&commit).map_err(odb_err)?.detach();
            before_cas(attempt);
            match self.cas(&full, tip, new_id, &sig, message) {
                Ok(()) => {
                    info!(ref_name = %full, oid = %new_id, retries, paths = planned.len(), "ledger commit");
                    if checked_out {
                        self.sync_checkout(&planned, base_tree)?;
                    }
                    let unsynced = self.sync_other_checkouts(&full, &planned, base_tree);
                    return Ok(CommitOutcome {
                        oid: new_id,
                        retries,
                        unsynced,
                    });
                }
                Err(CasError::Lost(why)) => {
                    retries += 1;
                    debug!(ref_name = %full, attempt, %why, "cas lost; re-reading tip");
                }
                Err(CasError::Fatal(e)) => return Err(e),
            }
        }
        warn!(ref_name = %full, attempts, "cas retries exhausted");
        Err(GitError::CasExhausted {
            ref_name: full,
            attempts,
        })
    }

    fn plan<'a>(
        &self,
        changes: &'a [(RelPath, Option<Vec<u8>>)],
    ) -> Result<Vec<Planned<'a>>, GitError> {
        let mut seen = std::collections::BTreeSet::new();
        let mut out = Vec::with_capacity(changes.len());
        for (path, bytes) in changes {
            if !seen.insert(path.as_str()) {
                return Err(GitError::BadPath(format!("{path} given twice")));
            }
            let blob = match bytes {
                Some(b) => Some((
                    self.gix.write_blob(b).map_err(odb_err)?.detach(),
                    b.as_slice(),
                )),
                None => None,
            };
            out.push(Planned { path, blob });
        }
        Ok(out)
    }

    fn is_checked_out(&self, full: &str) -> Result<bool, GitError> {
        let head = self.gix.head().map_err(|e| GitError::Ref(e.to_string()))?;
        Ok(self.work_dir().is_some()
            && head
                .referent_name()
                .is_some_and(|n| n.as_bstr() == full.as_bytes().as_bstr()))
    }

    fn read_ref(&self, full: &str) -> Result<Option<Oid>, GitError> {
        let r = self
            .gix
            .try_find_reference(full)
            .map_err(|e| GitError::Ref(e.to_string()))?;
        let Some(mut r) = r else { return Ok(None) };
        let id = r.peel_to_id().map_err(|e| GitError::Ref(e.to_string()))?;
        Ok(Some(id.detach()))
    }

    fn build_tree(&self, base: Oid, planned: &[Planned<'_>]) -> Result<Oid, GitError> {
        let mut editor = self.gix.edit_tree(base).map_err(odb_err)?;
        let base_tree = self.gix.find_tree(base).map_err(odb_err)?;
        for p in planned {
            match &p.blob {
                Some((id, _)) => {
                    let exec = base_tree
                        .lookup_entry_by_path(p.path.as_str())
                        .map_err(odb_err)?
                        .is_some_and(|e| e.mode().kind() == EntryKind::BlobExecutable);
                    let kind = if exec {
                        EntryKind::BlobExecutable
                    } else {
                        EntryKind::Blob
                    };
                    editor.upsert(p.path.as_str(), kind, *id).map_err(odb_err)?;
                }
                None => {
                    editor.remove(p.path.as_str()).map_err(odb_err)?;
                }
            }
        }
        Ok(editor.write().map_err(odb_err)?.detach())
    }

    fn cas(
        &self,
        full: &str,
        expected: Option<Oid>,
        new: Oid,
        sig: &gix::actor::Signature,
        message: &str,
    ) -> Result<(), CasError> {
        let subject = message.lines().next().unwrap_or("");
        let edit = RefEdit {
            change: Change::Update {
                log: LogChange {
                    mode: RefLog::AndReference,
                    force_create_reflog: false,
                    message: format!("commit: {subject}").into(),
                },
                expected: expected.map_or(PreviousValue::MustNotExist, |t| {
                    PreviousValue::MustExistAndMatch(Target::Object(t))
                }),
                new: Target::Object(new),
            },
            name: full
                .try_into()
                .map_err(|e: gix::validate::reference::name::Error| {
                    CasError::Fatal(GitError::Ref(e.to_string()))
                })?,
            deref: false,
        };
        let mut buf = gix::date::parse::TimeBuf::default();
        match self
            .gix
            .edit_references_as([edit], Some(sig.to_ref(&mut buf)))
        {
            Ok(_) => Ok(()),
            Err(e) => Err(classify(&e)),
        }
    }

    /// List the paths whose staged or on-disk content differs from both old and new content.
    fn check_local_edits(
        &self,
        planned: &[Planned<'_>],
        base_tree: Oid,
    ) -> Result<Vec<String>, GitError> {
        let mut blocked = Vec::new();
        let root = self.work_dir().expect("checked_out implies a worktree");
        let tree = self.gix.find_tree(base_tree).map_err(odb_err)?;
        let fresh = self.fresh_gix()?;
        let index = fresh
            .index_or_empty()
            .map_err(|e| GitError::Index(e.to_string()))?;
        // Filter-aware: disk bytes are converted to their git representation
        // (core.autocrlf, .gitattributes text/eol) before hashing, so a pure
        // line-ending rewrite by `git checkout` is never a local edit.
        let (mut pipeline, pipe_index) = fresh
            .filter_pipeline(None)
            .map_err(|e| GitError::Index(e.to_string()))?;
        for p in planned {
            let old = tree
                .lookup_entry_by_path(p.path.as_str())
                .map_err(odb_err)?
                .map(|e| e.object_id());
            let new = p.blob.as_ref().map(|(id, _)| *id);
            let staged = index.entry_by_path(p.path.as_str().into()).map(|e| e.id);
            let disk = match std::fs::File::open(root.join(p.path.as_str())) {
                Ok(f) => {
                    let bytes = to_git_bytes(&mut pipeline, &pipe_index, p.path, f)?;
                    Some(
                        gix::objs::compute_hash(
                            self.gix.object_hash(),
                            gix::object::Kind::Blob,
                            &bytes,
                        )
                        .map_err(odb_err)?,
                    )
                }
                Err(e) if e.kind() == std::io::ErrorKind::NotFound => None,
                Err(e) => return Err(GitError::io(format!("reading {}", p.path), e)),
            };
            if [staged, disk].iter().any(|s| *s != old && *s != new) {
                warn!(path = %p.path, "local edits block ledger checkout update");
                blocked.push(p.path.to_string());
            }
        }
        Ok(blocked)
    }

    /// Sync every other worktree that has `full` checked out; report those blocked by local edits.
    ///
    /// Failures here never undo the commit: they are logged and, where a checkout
    /// is known to be stale, reported in the returned list.
    fn sync_other_checkouts(
        &self,
        full: &str,
        planned: &[Planned<'_>],
        old_tree: Oid,
    ) -> Vec<UnsyncedCheckout> {
        let mut unsynced = Vec::new();
        let worktrees = match self.list_worktrees() {
            Ok(w) => w,
            Err(e) => {
                warn!(error = %e, "could not list worktrees; other checkouts not synced");
                return unsynced;
            }
        };
        let me = self.work_dir().and_then(|p| std::fs::canonicalize(p).ok());
        let short = full.strip_prefix("refs/heads/");
        for w in worktrees {
            if w.branch.as_deref() != short || short.is_none() {
                continue;
            }
            let Ok(canon) = std::fs::canonicalize(&w.path) else {
                debug!(path = %w.path.display(), "worktree directory missing; skipped");
                continue;
            };
            if Some(&canon) == me.as_ref() {
                continue;
            }
            match self.sync_one_other(&w.path, planned, old_tree) {
                Ok(None) => info!(path = %w.path.display(), "checkout synced to new tip"),
                Ok(Some(paths)) => {
                    warn!(path = %w.path.display(), ?paths, "checkout left stale: local edits");
                    unsynced.push(UnsyncedCheckout {
                        path: w.path,
                        paths_with_local_edits: paths,
                    });
                }
                Err(e) => warn!(path = %w.path.display(), error = %e, "checkout sync failed"),
            }
        }
        unsynced
    }

    /// Sync the checkout at `path`; `Some(paths)` when local edits blocked it.
    fn sync_one_other(
        &self,
        path: &Path,
        planned: &[Planned<'_>],
        old_tree: Oid,
    ) -> Result<Option<Vec<String>>, GitError> {
        let gix = gix::open(path).map_err(odb_err)?;
        let other = Repo {
            gix,
            runner: self.runner.clone(),
        };
        let blocked = other.check_local_edits(planned, old_tree)?;
        if !blocked.is_empty() {
            return Ok(Some(blocked));
        }
        other.sync_checkout(planned, old_tree)?;
        Ok(None)
    }

    /// Write files and stage entries for exactly the changed paths; nothing else in the index moves.
    fn sync_checkout(&self, planned: &[Planned<'_>], old_tree: Oid) -> Result<(), GitError> {
        let root = self.work_dir().expect("checked_out implies a worktree");
        let old = self.gix.find_tree(old_tree).map_err(odb_err)?;
        // Hold index.lock across read-modify-write so concurrent ledger writers
        // (and git itself) cannot lose each other's entries.
        let lock = gix::lock::File::acquire_to_update_resource(
            self.gix.index_path(),
            gix::lock::acquire::Fail::AfterDurationWithBackoff(std::time::Duration::from_secs(10)),
            None,
        )
        .map_err(|e| GitError::Index(e.to_string()))?;
        let mut index = match self.gix.open_index() {
            Ok(i) => i,
            Err(_) => gix::index::File::from_state(
                gix::index::State::new(self.gix.object_hash()),
                self.gix.index_path(),
            ),
        };
        for p in planned {
            let rel: &BString = &p.path.as_str().into();
            let disk = root.join(p.path.as_str());
            index.remove_entries(|_, path, _| path == rel.as_bstr());
            match &p.blob {
                Some((id, bytes)) => {
                    let exec = old
                        .lookup_entry_by_path(p.path.as_str())
                        .map_err(odb_err)?
                        .is_some_and(|e| e.mode().kind() == EntryKind::BlobExecutable);
                    write_file(&disk, bytes, exec)?;
                    let md = gix::index::fs::Metadata::from_path_no_follow(&disk)
                        .map_err(|e| GitError::io(format!("stat {}", p.path), e))?;
                    let stat = gix::index::entry::Stat::from_fs(&md)
                        .map_err(|e| GitError::Index(e.to_string()))?;
                    let mode = if exec {
                        gix::index::entry::Mode::FILE_EXECUTABLE
                    } else {
                        gix::index::entry::Mode::FILE
                    };
                    index.dangerously_push_entry(
                        stat,
                        *id,
                        gix::index::entry::Flags::empty(),
                        mode,
                        rel.as_bstr(),
                    );
                }
                None => match std::fs::remove_file(&disk) {
                    Ok(()) => {}
                    Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
                    Err(e) => return Err(GitError::io(format!("removing {}", p.path), e)),
                },
            }
        }
        index.sort_entries();
        index.remove_tree();
        write_index(&mut index, lock)?;
        debug!(paths = planned.len(), "checkout index and worktree updated");
        Ok(())
    }
}

/// Read `src` for `path` and return its git (clean-filtered) representation.
fn to_git_bytes(
    pipeline: &mut gix::filter::Pipeline<'_>,
    index: &gix::index::State,
    path: &RelPath,
    src: std::fs::File,
) -> Result<Vec<u8>, GitError> {
    use gix::filter::plumbing::pipeline::convert::ToGitOutcome;
    use std::io::Read;
    let ctx = |e: std::io::Error| GitError::io(format!("reading {path}"), e);
    let outcome = pipeline
        .convert_to_git(src, Path::new(path.as_str()), index)
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
    Ok(out)
}

/// Serialise `index` into the held `index.lock` and atomically commit it.
fn write_index(index: &mut gix::index::File, lock: gix::lock::File) -> Result<(), GitError> {
    let mut w = std::io::BufWriter::new(lock);
    index
        .write_to(&mut w, gix::index::write::Options::default())
        .map_err(|e| GitError::Index(e.to_string()))?;
    let lock = w
        .into_inner()
        .map_err(|e| GitError::io("flushing index.lock", e.into_error()))?;
    lock.commit().map_err(|e| GitError::Index(e.to_string()))?;
    Ok(())
}

fn write_file(path: &Path, bytes: &[u8], exec: bool) -> Result<(), GitError> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir)
            .map_err(|e| GitError::io(format!("mkdir {}", dir.display()), e))?;
    }
    std::fs::write(path, bytes)
        .map_err(|e| GitError::io(format!("writing {}", path.display()), e))?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mode = if exec { 0o755 } else { 0o644 };
        std::fs::set_permissions(path, std::fs::Permissions::from_mode(mode))
            .map_err(|e| GitError::io(format!("chmod {}", path.display()), e))?;
    }
    #[cfg(not(unix))]
    let _ = exec;
    Ok(())
}

/// Accept `main` as shorthand for `refs/heads/main`.
fn full_ref_name(name: &str) -> String {
    if name.starts_with("refs/") {
        name.to_owned()
    } else {
        format!("refs/heads/{name}")
    }
}

enum CasError {
    Lost(String),
    Fatal(GitError),
}

/// Split a failed ref transaction into "someone else moved the ref" and real failures.
fn classify(e: &gix::reference::edit::Error) -> CasError {
    use gix::reference::edit::Error as E;
    use gix::refs::file::transaction::prepare::Error as P;
    match e {
        E::FileTransactionPrepare(
            p @ (P::ReferenceOutOfDate { .. }
            | P::MustNotExist { .. }
            | P::MustExist { .. }
            | P::LockAcquire { .. }),
        ) => CasError::Lost(p.to_string()),
        _ => CasError::Fatal(GitError::Ref(e.to_string())),
    }
}
