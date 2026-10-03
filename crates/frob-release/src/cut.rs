//! `frob release cut VERSION`: the lockstep bump and the compiled CHANGELOG in one commit on the
//! base branch, then the per-binary annotated tags at that commit, then the ledger record.
//!
//! Design: `releases.md` sections 4, 5 and 6a, `git-io.md` (CAS ref writes, no `git` spawn
//! except push). The commit is written by `gob-git`'s compare-and-swap primitive
//! (`Repo::commit_paths`, the one `land` and the ledger use): it re-reads a moved base and
//! re-applies the changes, never merges, and gives up with `E-GIT-CAS-EXHAUSTED`. The tags are
//! created in process (`Repo::create_annotated_tag`). The ledger is behind the [`CutLedger`]
//! trait so this module needs no ledger of its own; `frob release cut` implements it over the
//! milestone's event log.
//!
//! # Order
//!
//! 1. Refusals, in this order: not on the base branch, a dirty tree, the version already cut
//!    (recorded), a tag that exists without being this cut's own.
//! 2. [`CutLedger::clear`] (the readiness gate; records an override). Fresh cuts only.
//! 3. Bump and changelog compile in the working tree, collect exactly the changed paths, one
//!    commit `chore(release): cut VERSION`; the tree is restored when anything fails first.
//! 4. One annotated tag per configured product (`[release] products`, `tag`) at that commit.
//! 5. [`CutLedger::record`]: a `cut` event (version, commit, tag names and oids), then the
//!    milestone `transition` to released.
//! 6. With `push`, the base branch and the tags go to `origin`.
//!
//! # Failure matrix (every row is resumable by running the same command again)
//!
//! | Failure | State left | Re-run |
//! |---|---|---|
//! | before the commit (bump, compile, CAS exhausted) | working tree restored, nothing else | starts fresh |
//! | after the commit, before any tag | commit on base, no tags, no event | finds the commit by its subject, tags and records, skips bump, compile and the gate |
//! | between two tags | commit and some tags | creates the missing tags, records |
//! | after the tags, before the `cut` event | commit and all tags | tags already point at the cut commit, so records only |
//! | after the `cut` event, before the transition | event written, milestone open | transitions only |
//! | after the record, push fails | everything local and recorded | the version counts as cut; run the printed `git push` |
//!
//! A tag of the same name that points elsewhere is never moved: it is `E-CUT-TAG-EXISTS`.
//! A recorded cut (event and released milestone) is `E-CUT-ALREADY`.
//!
//! The working tree must be on the base branch: the bump edits files in place, and the commit
//! is then moved onto the ref with the checkout synced by `gob-git`.

use std::path::Path;

use frob_pm::event::{CutData, TagRecord};
use gob_git::{CommitOptions, Oid, RelPath, Repo, StatusKind, StatusOptions};

use crate::bump::{self, BumpError, BumpOptions};
use crate::{Mode, Options, ProductTags, ReleaseError, TicketResolver};

/// How many first-parent commits are searched for an earlier cut commit when resuming.
const RESUME_SCAN: usize = 500;

/// Where a cut stops early; used by tests to simulate a crash, never set by the CLI.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Phase {
    /// Stop right after the commit, before any tag.
    Commit,
    /// Stop after the tags, before the ledger record.
    Tags,
}

/// What `release cut` needs from the ledger; implemented over the milestone's event log.
pub trait CutLedger {
    /// The readiness gate, run only for a fresh cut: refuse with [`CutError::NotReady`], or record an override and allow.
    ///
    /// # Errors
    /// [`CutError::NotReady`] when the milestone is not ready and there is no override.
    fn clear(&mut self) -> Result<(), CutError>;

    /// True when the cut of this version is fully recorded (a `cut` event and a released milestone).
    ///
    /// # Errors
    /// [`CutError::Ledger`] when the ledger cannot be read.
    fn recorded(&self) -> Result<bool, CutError>;

    /// Record the cut and release the milestone; must be safe to repeat after a partial record.
    ///
    /// # Errors
    /// [`CutError::Ledger`] when the ledger cannot be written.
    fn record(&mut self, data: &CutData) -> Result<(), CutError>;
}

/// Inputs of one cut.
#[derive(Debug, Clone)]
pub struct CutPlan<'a> {
    /// Repository root (the checkout on the base branch).
    pub root: &'a Path,
    /// The version, `MAJOR.MINOR.PATCH[-pre]`.
    pub version: String,
    /// Changelog section date, `YYYY-MM-DD`.
    pub date: String,
    /// Short name of the base branch the commit lands on.
    pub base: String,
    /// Push the base branch and the tags to `origin` afterwards.
    pub push: bool,
    /// Stop early to simulate a crash (tests only).
    pub stop_after: Option<Phase>,
}

/// What a cut did.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CutOutcome {
    /// The version cut.
    pub version: String,
    /// The release commit.
    pub commit: Oid,
    /// Every tag at that commit, in configured product order.
    pub tags: Vec<TagRecord>,
    /// True when an earlier, interrupted cut was finished instead of starting one.
    pub resumed: bool,
    /// True when the push ran and succeeded.
    pub pushed: bool,
    /// Paths the release commit changed.
    pub files: Vec<String>,
}

/// Why a cut refused or failed; [`CutError::is_refusal`] separates a teaching refusal from an internal failure.
#[derive(Debug, thiserror::Error)]
pub enum CutError {
    /// The checkout is not on the base branch.
    #[error("E-CUT-NOT-ON-BASE: the checkout is on {current}, not the base branch {base}")]
    NotOnBase {
        /// The configured base branch.
        base: String,
        /// What is checked out (`detached` when nothing).
        current: String,
    },
    /// The tree has uncommitted changes.
    #[error("E-CUT-DIRTY: the tree has uncommitted changes: {}", .0.join(", "))]
    Dirty(Vec<String>),
    /// This version's cut is already recorded.
    #[error("E-CUT-ALREADY: {0} is already cut and recorded; cut the next version")]
    Already(String),
    /// A tag of this name exists and is not this cut's.
    #[error("E-CUT-TAG-EXISTS: tag {0} already exists and is not at a cut commit of this version")]
    TagExists(String),
    /// The milestone is not ready and there is no override.
    #[error("E-CUT-NOT-READY: {0}")]
    NotReady(String),
    /// The milestone for the version does not exist.
    #[error("E-CUT-NO-MILESTONE: no milestone for {0}")]
    NoMilestone(String),
    /// The bump and compile changed nothing, so there is nothing to commit.
    #[error(
        "E-CUT-NOTHING: the bump and the changelog compile changed no file; there is nothing to cut"
    )]
    Nothing,
    /// The version bump failed.
    #[error("E-CUT-BUMP: {0}")]
    Bump(#[from] BumpError),
    /// The changelog compile failed.
    #[error("E-CUT-CHANGELOG: {0}")]
    Changelog(#[from] ReleaseError),
    /// Git failed.
    #[error("E-CUT-GIT: {0}")]
    Git(#[from] gob_git::GitError),
    /// The ledger could not be read or written.
    #[error("E-CUT-LEDGER: {0}")]
    Ledger(String),
    /// Restoring or reading a file failed.
    #[error("E-CUT-IO: {0}")]
    Io(String),
    /// The push failed after the cut was recorded.
    #[error("E-CUT-PUSH: the cut is recorded locally but the push failed: {0}")]
    Push(String),
    /// A test stop point was reached.
    #[error("E-CUT-STOPPED: stopped after {0:?}")]
    Stopped(Phase),
}

impl CutError {
    /// True for a refusal the caller can act on (exit 3); false for an internal failure.
    #[must_use]
    pub fn is_refusal(&self) -> bool {
        !matches!(
            self,
            Self::Ledger(_)
                | Self::Io(_)
                | Self::Push(_)
                | Self::Stopped(_)
                | Self::Bump(BumpError::Io { .. })
                | Self::Changelog(ReleaseError::Io { .. })
                | Self::Git(_)
        ) || matches!(self, Self::Git(gob_git::GitError::CasExhausted { .. }))
    }

    /// The command or step that fixes the refusal.
    #[must_use]
    pub fn remedy(&self, version: &str, base: &str) -> String {
        match self {
            Self::NotOnBase { .. } => format!("git switch {base}, then frob release cut {version}"),
            Self::Dirty(_) => "commit or stash the changes, then rerun".to_owned(),
            Self::Already(_) => "frob release status <next version>".to_owned(),
            Self::TagExists(t) => format!(
                "inspect it with `git show {t}`; delete it only if it is yours and unpushed"
            ),
            Self::NotReady(_) => format!(
                "frob release status {version}, fix the blockers, or frob release cut {version} --override --reason <text>"
            ),
            Self::NoMilestone(_) => format!("frob milestone new {version} --goal <text>"),
            Self::Nothing => {
                "bump or add changelog fragments first; see frob release status".to_owned()
            }
            Self::Changelog(_) => format!("frob release changelog --check --version {version}"),
            Self::Bump(_) => format!("frob release bump {version} --dry-run"),
            Self::Git(_) => format!("rerun frob release cut {version} (it resumes)"),
            _ => format!("rerun frob release cut {version}"),
        }
    }
}

/// The subject of the release commit; resume finds an interrupted cut by it.
#[must_use]
pub fn commit_subject(version: &str) -> String {
    format!("chore(release): cut {version}")
}

/// Cut `plan.version`: refuse, gate, commit, tag, record, optionally push; or finish an interrupted cut.
///
/// # Errors
/// [`CutError`]; see the module's failure matrix for the state each failure leaves and how to resume.
pub fn cut(
    plan: &CutPlan<'_>,
    resolver: &dyn TicketResolver,
    ledger: &mut dyn CutLedger,
) -> Result<CutOutcome, CutError> {
    let repo = Repo::discover(plan.root)?;
    let current = repo.current_branch()?;
    if current.as_deref() != Some(plan.base.as_str()) {
        return Err(CutError::NotOnBase {
            base: plan.base.clone(),
            current: current.unwrap_or_else(|| "a detached HEAD".to_owned()),
        });
    }
    let products = ProductTags::load(plan.root)?;
    let dirty = dirty_paths(&repo)?;
    if !dirty.is_empty() {
        return Err(CutError::Dirty(dirty));
    }
    if ledger.recorded()? {
        return Err(CutError::Already(plan.version.clone()));
    }
    let subject = commit_subject(&plan.version);
    let earlier = repo
        .first_parent_subjects(&plan.base, RESUME_SCAN)?
        .into_iter()
        .find(|(_, s)| *s == subject)
        .map(|(oid, _)| oid);
    let mut existing = Vec::new();
    for name in products.tag_names(&plan.version) {
        if let Some(info) = repo.find_tag(&name)? {
            if earlier != Some(info.commit) {
                tracing::warn!(tag = %name, "cut refused: tag exists elsewhere");
                return Err(CutError::TagExists(name));
            }
            existing.push(TagRecord {
                name,
                object: info.object.to_string(),
                commit: info.commit.to_string(),
            });
        }
    }
    let (commit, files, resumed) = if let Some(oid) = earlier {
        tracing::info!(version = %plan.version, commit = %oid, "resuming an interrupted cut");
        (oid, Vec::new(), true)
    } else {
        ledger.clear()?;
        let (oid, files) = commit_release(&repo, plan, resolver)?;
        (oid, files, false)
    };
    if plan.stop_after == Some(Phase::Commit) {
        return Err(CutError::Stopped(Phase::Commit));
    }
    let mut tags = Vec::new();
    for product in products.products() {
        let name = products.tag_name(product, &plan.version);
        if let Some(t) = existing.iter().find(|t| t.name == name) {
            tags.push(t.clone());
            continue;
        }
        let msg = products.tag_message(product, &plan.version);
        let object = repo.create_annotated_tag(&name, commit, &msg, None)?;
        tags.push(TagRecord {
            name,
            object: object.to_string(),
            commit: commit.to_string(),
        });
    }
    if plan.stop_after == Some(Phase::Tags) {
        return Err(CutError::Stopped(Phase::Tags));
    }
    ledger.record(&CutData {
        version: plan.version.clone(),
        commit: commit.to_string(),
        tags: tags.clone(),
    })?;
    let pushed = plan.push && push(&repo, &plan.base, &tags)?;
    tracing::info!(version = %plan.version, %commit, tags = tags.len(), resumed, pushed, "release cut");
    Ok(CutOutcome {
        version: plan.version.clone(),
        commit,
        tags,
        resumed,
        pushed,
        files,
    })
}

/// Uncommitted paths of the checkout (`.frob/` is frob's own state).
fn dirty_paths(repo: &Repo) -> Result<Vec<String>, CutError> {
    let mut paths: Vec<String> = repo
        .status(&StatusOptions::default())?
        .into_iter()
        .map(|e| e.path)
        .filter(|p| !p.starts_with(".frob/"))
        .collect();
    paths.dedup();
    Ok(paths)
}

/// Bump and compile in the tree, then commit exactly the changed paths onto the base by CAS; restore the tree on failure.
fn commit_release(
    repo: &Repo,
    plan: &CutPlan<'_>,
    resolver: &dyn TicketResolver,
) -> Result<(Oid, Vec<String>), CutError> {
    let tip = repo.rev_parse(&plan.base)?;
    let result = edit_and_commit(repo, plan, resolver);
    if result.is_err() {
        tracing::error!(version = %plan.version, "cut failed before the commit; restoring the tree");
        restore(repo, plan.root, tip);
    }
    result
}

/// The fallible part of [`commit_release`].
fn edit_and_commit(
    repo: &Repo,
    plan: &CutPlan<'_>,
    resolver: &dyn TicketResolver,
) -> Result<(Oid, Vec<String>), CutError> {
    bump::run(
        plan.root,
        &BumpOptions {
            version: plan.version.clone(),
            dry_run: false,
            allow_downgrade: false,
        },
    )?;
    crate::run(
        plan.root,
        &Options {
            version: plan.version.clone(),
            date: plan.date.clone(),
            mode: Mode::Write,
        },
        resolver,
    )?;
    let mut changes: Vec<(RelPath, Option<Vec<u8>>)> = Vec::new();
    let mut files = Vec::new();
    for entry in repo.status(&StatusOptions::default())? {
        if entry.path.starts_with(".frob/") {
            continue;
        }
        let bytes = match entry.kind {
            StatusKind::Deleted => None,
            _ => Some(
                std::fs::read(plan.root.join(&entry.path))
                    .map_err(|e| CutError::Io(format!("read {}: {e}", entry.path)))?,
            ),
        };
        files.push(entry.path.clone());
        changes.push((RelPath::new(entry.path)?, bytes));
    }
    changes.dedup_by(|a, b| a.0 == b.0);
    files.dedup();
    if changes.is_empty() {
        return Err(CutError::Nothing);
    }
    let message = format!(
        "{}\n\nLockstep version bump and compiled CHANGELOG.md for {}, made by frob release cut.\n",
        commit_subject(&plan.version),
        plan.version
    );
    let out = repo.commit_paths(
        &format!("refs/heads/{}", plan.base),
        &changes,
        &message,
        &CommitOptions::default(),
    )?;
    tracing::info!(commit = %out.oid, retries = out.retries, files = files.len(), "release commit written");
    Ok((out.oid, files))
}

/// Put every path the cut touched back to its content at `tip`, removing files that did not exist there.
fn restore(repo: &Repo, root: &Path, tip: Oid) {
    let Ok(entries) = repo.status(&StatusOptions::default()) else {
        tracing::error!("cannot read status to restore the tree");
        return;
    };
    let rev = tip.to_string();
    for e in entries
        .into_iter()
        .filter(|e| !e.path.starts_with(".frob/"))
    {
        let path = root.join(&e.path);
        let done = match repo.read_blob_at(&rev, &e.path) {
            Ok(Some(bytes)) => std::fs::write(&path, bytes),
            Ok(None) => std::fs::remove_file(&path),
            Err(err) => {
                tracing::error!(path = %e.path, %err, "cannot read the original to restore");
                continue;
            }
        };
        if let Err(err) = done {
            tracing::error!(path = %e.path, %err, "could not restore");
        }
    }
}

/// Push the base branch and every tag to `origin`; true when all went.
fn push(repo: &Repo, base: &str, tags: &[TagRecord]) -> Result<bool, CutError> {
    repo.push("origin", &format!("refs/heads/{base}"))
        .map_err(|e| CutError::Push(e.to_string()))?;
    for t in tags {
        repo.push("origin", &format!("refs/tags/{}", t.name))
            .map_err(|e| CutError::Push(e.to_string()))?;
    }
    tracing::info!(tags = tags.len(), "cut pushed to origin");
    Ok(true)
}
