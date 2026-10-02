//! `work`, `start` and `requeue`: lease, worktree, branch and transition in one call.
//!
//! Order for `work`: resolve and vet the ticket, take (or recognise, or steal)
//! the lease, create the worktree on `ticket/<handle>` from the base branch,
//! merge the base, then append the `in-progress` transition carrying the lease
//! summary. A failure after a fresh lease releases it again. A repeat by the
//! same holder (actor plus worktree path) changes nothing and reports
//! `already`; anyone else gets `E-LEASE-HELD` naming the holder.

use std::path::{Component, Path, PathBuf};

use frob_lease::{Holder, Lease, LeaseError, LeaseStore};
use frob_ledger::model::{Category, CommentSubtype, TicketType};
use frob_ledger::{Ledger, TicketId};
use gob_diagnostics::{Refusal, RefusalClass};
use gob_git::MergeOutcome;

use crate::config::WorktreeConfig;
use crate::error::WorktreeError;

/// Options of `work`.
#[derive(Debug, Clone, Default)]
pub struct WorkOptions {
    /// Create the worktree here instead of under `[worktree] dir`.
    pub worktree: Option<PathBuf>,
    /// Take over a lease held by someone else, with this reason.
    pub steal: Option<String>,
}

/// What `work` and `start` did.
#[derive(Debug, Clone)]
pub struct Started {
    /// The ticket.
    pub id: TicketId,
    /// Its handle with `~`.
    pub handle: String,
    /// The holder's worktree (the current checkout for `start`).
    pub path: PathBuf,
    /// The branch checked out there (`work` only).
    pub branch: Option<String>,
    /// The lease in force.
    pub lease: Lease,
    /// True when nothing changed: same holder, worktree present, ticket already in progress.
    pub already: bool,
    /// True when this call created the worktree.
    pub created_worktree: bool,
    /// How merging the base went: `up-to-date`, `fast-forward`, `merged` or `conflicts`.
    pub merge: Option<String>,
    /// Paths left conflicted by the base merge.
    pub conflicts: Vec<String>,
    /// The previous holder when the lease was stolen.
    pub stolen_from: Option<Holder>,
    /// Non-fatal notices for the caller.
    pub warnings: Vec<String>,
}

/// What `requeue` did.
#[derive(Debug, Clone)]
pub struct Requeued {
    /// The ticket.
    pub id: TicketId,
    /// Its handle with `~`.
    pub handle: String,
    /// The lease that was released, if there was one.
    pub released: Option<Lease>,
    /// True when there was no lease to release and the ticket was not in progress.
    pub already: bool,
}

/// Where the holder works: a fresh worktree for `work`, the current checkout for `start`.
enum Plan {
    Work { override_path: Option<PathBuf> },
    Start { cwd: PathBuf },
}

/// The pieces `work`, `start` and `requeue` combine: ledger, leases and worktree settings.
#[derive(Debug)]
pub struct Workspace<'a> {
    /// The open ledger (also gives the repository and the actor).
    pub ledger: &'a Ledger,
    /// The lease store of the same clone.
    pub leases: &'a LeaseStore,
    /// `[worktree]` settings.
    pub config: &'a WorktreeConfig,
}

impl Workspace<'_> {
    /// Lease the ticket, create its worktree and branch, merge the base and move it to `in-progress`.
    ///
    /// # Errors
    ///
    /// `E-TICKET-NOT-WORKABLE` for epics, done tickets and tickets already in
    /// progress for someone else; `E-LEASE-HELD` when another holder has the
    /// ticket or an overlapping scope; `E-WORKTREE-EXISTS`; ledger and git failures.
    pub fn work(&self, ticket: &str, opts: &WorkOptions) -> Result<Started, WorktreeError> {
        self.begin(
            ticket,
            &Plan::Work {
                override_path: opts.worktree.clone(),
            },
            opts.steal.as_deref(),
        )
    }

    /// `work` without the worktree: the lease is held for the checkout at `cwd`.
    ///
    /// # Errors
    ///
    /// The same refusals as [`Workspace::work`], minus the worktree ones.
    pub fn start(
        &self,
        ticket: &str,
        cwd: &Path,
        steal: Option<&str>,
    ) -> Result<Started, WorktreeError> {
        self.begin(ticket, &Plan::Start { cwd: clean(cwd) }, steal)
    }

    /// Release the lease on `ticket` and move it back to `todo`.
    ///
    /// # Errors
    ///
    /// A usage error without a reason, `E-LEASE-HELD` when another actor holds a
    /// live lease, `E-TICKET-NOT-WORKABLE` for a done ticket, ledger failures.
    pub fn requeue(&self, ticket: &str, reason: &str) -> Result<Requeued, WorktreeError> {
        if reason.trim().is_empty() {
            return Err(WorktreeError::Usage(
                "requeue needs a non-empty --reason".to_owned(),
            ));
        }
        let id = self.ledger.resolve(ticket)?;
        let view = self.ledger.show(id)?;
        let handle = view.summary.handle.clone();
        if view.summary.category == Category::Done {
            return Err(WorktreeError::not_workable(
                format!("{handle} is done and cannot be requeued"),
                Some(format!("frob ticket reopen {handle} --reason <why>")),
            ));
        }
        let actor = self.ledger.actor()?;
        let released = self
            .leases
            .release(id, Some(&actor))
            .map_err(|e| held_refusal(e, id, &handle))?;
        let mut already = released.is_none();
        if view.summary.category == Category::InProgress {
            let applied =
                self.ledger
                    .transition(id, Category::Todo, None, Some(reason.to_owned()))?;
            already &= applied.already;
        }
        tracing::info!(ticket = %id, released = released.is_some(), reason, "ticket requeued");
        Ok(Requeued {
            id,
            handle,
            released,
            already,
        })
    }

    fn begin(
        &self,
        ticket: &str,
        plan: &Plan,
        steal: Option<&str>,
    ) -> Result<Started, WorktreeError> {
        let id = self.ledger.resolve(ticket)?;
        let view = self.ledger.show(id)?;
        let handle = view.summary.handle.clone();
        let scope = view.ticket.front.scope.clone();
        let actor = self.ledger.actor()?;
        let existing = self.leases.live_lease(id)?;
        let (path, branch) = self.locate(plan, &handle, existing.as_ref(), &actor);
        let holder = Holder {
            actor,
            worktree: path.clone(),
        };
        vet(
            view.summary.ty,
            view.summary.category,
            &handle,
            existing.is_some(),
        )?;

        let (lease, fresh, stolen_from) = self.take(id, &handle, &holder, &scope, steal)?;
        let outcome = self.build(plan, id, &handle, &lease, branch.as_deref());
        let built = match outcome {
            Ok(b) => b,
            Err(e) => {
                if fresh {
                    self.rollback(id, &holder);
                }
                return Err(e);
            }
        };
        let summary = format!(
            "lease: {} in {}; scope: {}; ttl {}s",
            holder.actor,
            path.display(),
            lease.scope.join(", "),
            lease.ttl_secs
        );
        let applied = match self
            .ledger
            .transition(id, Category::InProgress, None, Some(summary))
        {
            Ok(a) => a,
            Err(e) => {
                if fresh {
                    self.rollback(id, &holder);
                }
                return Err(e.into());
            }
        };
        if let Some(prev) = &stolen_from {
            let note = format!(
                "lease stolen from {prev} by {holder}: {}",
                steal.unwrap_or_default()
            );
            self.ledger.comment(id, CommentSubtype::Note, &note)?;
        }
        let mut warnings = Vec::new();
        if lease.scope.is_empty() {
            warnings.push(format!(
                "{handle} has an empty scope; SCOPE001 will flag every changed file"
            ));
        }
        if !built.conflicts.is_empty() {
            warnings.push(format!(
                "merging the base left {} conflicted path(s); resolve them in {}",
                built.conflicts.len(),
                path.display()
            ));
        }
        let already = !fresh && stolen_from.is_none() && !built.created && applied.already;
        tracing::info!(ticket = %id, path = %path.display(), already, created = built.created, "ticket started");
        Ok(Started {
            id,
            handle,
            path,
            branch,
            lease,
            already,
            created_worktree: built.created,
            merge: built.merge,
            conflicts: built.conflicts,
            stolen_from,
            warnings,
        })
    }

    /// Acquire the lease (or steal it): the lease, whether it is new, and the previous holder when stolen.
    fn take(
        &self,
        id: TicketId,
        handle: &str,
        holder: &Holder,
        scope: &[String],
        steal: Option<&str>,
    ) -> Result<(Lease, bool, Option<Holder>), WorktreeError> {
        match self.leases.acquire(id, holder, scope) {
            Ok(a) => Ok((a.lease, !a.already, None)),
            Err(LeaseError::Held { ticket, .. }) if steal.is_some() && ticket == id => {
                let reason = steal.unwrap_or_default();
                let s = self.leases.steal(id, holder, reason)?;
                Ok((s.lease, false, Some(s.previous)))
            }
            Err(e) => Err(held_refusal(e, id, handle)),
        }
    }

    /// Create (or recognise) the worktree and merge the base into it.
    fn build(
        &self,
        plan: &Plan,
        id: TicketId,
        handle: &str,
        lease: &Lease,
        branch: Option<&str>,
    ) -> Result<Built, WorktreeError> {
        let (Plan::Work { .. }, Some(branch)) = (plan, branch) else {
            return Ok(Built::default());
        };
        let path = &lease.holder.worktree;
        let base = base_branch(self.ledger);
        let repo = self.ledger.repo();
        let exists = path.join(".git").exists();
        if !exists {
            if path.exists() && std::fs::read_dir(path).is_ok_and(|mut d| d.next().is_some()) {
                return Err(WorktreeError::PathExists(path.clone()));
            }
            if let Some(parent) = path.parent() {
                std::fs::create_dir_all(parent).map_err(|e| {
                    WorktreeError::Config(format!("creating {}: {e}", parent.display()))
                })?;
            }
            repo.worktree_add(path, branch, &base)?;
            tracing::info!(ticket = %id, handle, path = %path.display(), branch, base = %base, "worktree created");
        }
        let (merge, conflicts) = if exists {
            (None, Vec::new())
        } else {
            match repo.merge_branch(path, &base)? {
                MergeOutcome::UpToDate => (Some("up-to-date".to_owned()), Vec::new()),
                MergeOutcome::FastForward => (Some("fast-forward".to_owned()), Vec::new()),
                MergeOutcome::Merged => (Some("merged".to_owned()), Vec::new()),
                MergeOutcome::Conflicts(c) => (Some("conflicts".to_owned()), c),
            }
        };
        Ok(Built {
            created: !exists,
            merge,
            conflicts,
        })
    }

    fn rollback(&self, id: TicketId, holder: &Holder) {
        match self.leases.release(id, Some(&holder.actor)) {
            Ok(_) => tracing::warn!(ticket = %id, "lease rolled back after a failed start"),
            Err(e) => tracing::error!(ticket = %id, error = %e, "lease rollback failed"),
        }
    }

    /// The holder's worktree path and branch for `plan`.
    ///
    /// Without an explicit path a live lease of the same actor sitting in the
    /// same parent directory is reused, so a handle that grew longer since the
    /// worktree was made does not orphan it.
    fn locate(
        &self,
        plan: &Plan,
        handle: &str,
        existing: Option<&Lease>,
        actor: &str,
    ) -> (PathBuf, Option<String>) {
        match plan {
            Plan::Start { cwd } => (cwd.clone(), None),
            Plan::Work { override_path } => {
                let name = handle.trim_start_matches('~');
                let path = match override_path {
                    Some(p) if p.is_absolute() => clean(p),
                    Some(p) => clean(&self.cwd().join(p)),
                    None => {
                        let computed = self.default_path(name);
                        existing
                            .filter(|l| {
                                l.holder.actor == actor
                                    && l.holder.worktree.parent() == computed.parent()
                            })
                            .map_or(computed, |l| l.holder.worktree.clone())
                    }
                };
                let dir_name = path
                    .file_name()
                    .map_or_else(|| name.to_owned(), |n| n.to_string_lossy().into_owned());
                (path, Some(format!("ticket/{dir_name}")))
            }
        }
    }

    fn cwd(&self) -> PathBuf {
        self.ledger
            .repo()
            .work_dir()
            .map_or_else(|| PathBuf::from("."), Path::to_path_buf)
    }

    fn primary_root(&self) -> PathBuf {
        let repo = self.ledger.repo();
        repo.list_worktrees()
            .ok()
            .and_then(|w| w.into_iter().next().map(|i| i.path))
            .unwrap_or_else(|| self.cwd())
    }

    fn default_path(&self, name: &str) -> PathBuf {
        let primary = self.primary_root();
        let repo_name = primary
            .file_name()
            .map_or_else(|| "repo".to_owned(), |n| n.to_string_lossy().into_owned());
        let dir = self.config.dir.replace("{repo}", &repo_name);
        let dir = PathBuf::from(dir);
        let parent = if dir.is_absolute() {
            dir
        } else {
            primary.join(dir)
        };
        clean(&parent.join(name))
    }
}

/// What creating the worktree did.
#[derive(Debug, Default)]
struct Built {
    created: bool,
    merge: Option<String>,
    conflicts: Vec<String>,
}

/// The short name of the base branch: `[tickets] ref` without `refs/heads/`.
pub fn base_branch(ledger: &Ledger) -> String {
    let r = &ledger.config().ref_name;
    r.strip_prefix("refs/heads/").unwrap_or(r).to_owned()
}

/// Refuse tickets that cannot be worked; `leased` lets an in-progress ticket through to the lease check, which names the holder.
fn vet(
    ty: TicketType,
    category: Category,
    handle: &str,
    leased: bool,
) -> Result<(), WorktreeError> {
    if ty == TicketType::Epic {
        return Err(WorktreeError::not_workable(
            format!("{handle} is an epic; work one of its children"),
            Some(format!("frob ticket show {handle}")),
        ));
    }
    match category {
        Category::Todo | Category::Triage => Ok(()),
        Category::InProgress if leased => Ok(()),
        Category::InProgress => Err(WorktreeError::not_workable(
            format!("{handle} is in progress with no live lease"),
            Some(format!("frob requeue {handle} --reason <why>")),
        )),
        Category::Done => Err(WorktreeError::not_workable(
            format!("{handle} is done"),
            Some(format!("frob ticket reopen {handle} --reason <why>")),
        )),
    }
}

/// Turn a held lease into the refusal for `work`, with the right remedy; pass other errors through.
fn held_refusal(e: LeaseError, id: TicketId, handle: &str) -> WorktreeError {
    let LeaseError::Held { ticket, .. } = &e else {
        return e.into();
    };
    let remedy = if *ticket == id {
        format!("frob work {handle} --steal --reason <why>")
    } else {
        format!("wait for lease holder of {ticket} to finish, then rerun: frob work {handle}")
    };
    match e.to_refusal() {
        Some(r) => WorktreeError::Refused(r.with_remedy(remedy)),
        None => WorktreeError::Refused(Refusal::new(
            "E-LEASE-HELD",
            RefusalClass::GuardRetryByWaiting,
            e.to_string(),
        )),
    }
}

/// Lexically resolve `.` and `..` so equal paths compare equal.
pub fn clean(path: &Path) -> PathBuf {
    let mut out = PathBuf::new();
    for c in path.components() {
        match c {
            Component::CurDir => {}
            Component::ParentDir => {
                if !out.pop() {
                    out.push("..");
                }
            }
            other => out.push(other.as_os_str()),
        }
    }
    out
}
