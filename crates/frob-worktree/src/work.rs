//! `work`, `start` and `requeue`: lease, worktree, branch and transition in one call.
//!
//! Order for `work`: resolve and vet the ticket, take (or recognise, or steal)
//! the lease, create the worktree on `ticket/<handle>` from the base branch,
//! merge the base, then append the `in-progress` transition carrying the lease
//! summary. A failure after a fresh lease releases it again. A repeat by the
//! same holder (actor plus worktree path) changes nothing and reports
//! `already`; anyone else gets `E-LEASE-HELD` naming the holder. The repository
//! WIP count runs inside the lease-store lock (`acquire_admitting`), so the check
//! and the lease are one critical section.

// frob:ticket 01M40Q3S4T9QTYX0Z1MPAZP9JM

use gob_path::Shown;
use std::path::{Component, Path, PathBuf};
use std::time::Duration;

use frob_lease::error::SAME_TICKET;
use frob_lease::{Holder, Lease, LeaseError, LeaseStore};
use frob_ledger::model::{Category, CommentSubtype, TicketType};
use frob_ledger::{Ledger, TicketId};
use gob_diagnostics::{Refusal, RefusalClass};
use gob_exec::{Outcome, Program, Spec};
use gob_git::{MergeOutcome, Repo};

use crate::claim::{E_CLAIM_LOST, Publication, W_CLAIM_UNPUBLISHED};
use crate::config::WorktreeConfig;
use crate::error::WorktreeError;

/// Options of `work`.
#[derive(Debug, Clone, Default)]
pub struct WorkOptions {
    /// Create the worktree here instead of under `[worktree] dir`.
    pub worktree: Option<PathBuf>,
    /// Take over a lease held by someone else, with this reason.
    pub steal: Option<String>,
    /// Start a ticket outside the active cycle anyway, assigning it as an over-commit with this reason.
    pub unplanned: Option<String>,
    /// Seconds to queue for a blocked scope (`work --wait`); 0 refuses at once (frob:ticket 01M41ZRNYEWRY4V2MXT3WMXBBJ).
    pub wait_secs: u64,
    /// Apply the sprint gate (`[pm] sprint_gate`): refuse a ticket outside the active cycle; off in a default `WorkOptions`.
    pub sprint_gate: bool,
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

/// The per-call options of [`Workspace::begin`]: the two reasoned ways past a refusal (stealing a lease, starting unplanned work) and whether the sprint gate applies.
#[derive(Debug, Clone, Copy)]
struct Escapes<'a> {
    steal: Option<&'a str>,
    unplanned: Option<&'a str>,
    sprint_gate: bool,
    wait_secs: u64,
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
            Escapes {
                steal: opts.steal.as_deref(),
                unplanned: opts.unplanned.as_deref(),
                sprint_gate: opts.sprint_gate,
                wait_secs: opts.wait_secs,
            },
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
        self.start_with(
            ticket,
            cwd,
            &WorkOptions {
                steal: steal.map(str::to_owned),
                ..WorkOptions::default()
            },
        )
    }

    /// [`Workspace::start`] with the `steal`, `unplanned` and `sprint_gate` options of `opts` (`worktree` is unused).
    ///
    /// # Errors
    ///
    /// As [`Workspace::start`], plus the cycle gates.
    pub fn start_with(
        &self,
        ticket: &str,
        cwd: &Path,
        opts: &WorkOptions,
    ) -> Result<Started, WorktreeError> {
        self.begin(
            ticket,
            &Plan::Start { cwd: clean(cwd) },
            Escapes {
                steal: opts.steal.as_deref(),
                unplanned: opts.unplanned.as_deref(),
                sprint_gate: opts.sprint_gate,
                wait_secs: opts.wait_secs,
            },
        )
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
        Escapes {
            steal,
            unplanned,
            sprint_gate,
            wait_secs,
        }: Escapes<'_>,
    ) -> Result<Started, WorktreeError> {
        let id = self.ledger.resolve(ticket)?;
        let view = self.ledger.show(id)?;
        let handle = view.summary.handle.clone();
        let scope = view.ticket.front.scope.clone();
        let actor = self.ledger.actor()?;
        let existing = self.leases.live_lease(id)?;
        let resumed =
            self.resumed_worktree(plan, view.summary.category, &handle, existing.is_some());
        let (path, branch) =
            self.locate(plan, &handle, existing.as_ref(), &actor, resumed.as_deref());
        let holder = Holder {
            actor,
            worktree: path.clone(),
        };
        let leased = existing.is_some() || resumed.is_some();
        vet(view.summary.ty, view.summary.category, &handle, leased)?;
        // An in-progress ticket with a live lease already holds its slot (re-entry, steal).
        let needs_slot = !(view.summary.category == Category::InProgress && existing.is_some());
        if needs_slot {
            self.cycle_gates((id, view.summary.class, &handle), sprint_gate, unplanned)?;
        }
        let taking = crate::wip::Taking {
            id,
            handle: &handle,
            class: view.summary.class,
        };
        let (lease, fresh, stolen_from) =
            self.take_waiting(taking, needs_slot, (&holder, &scope), steal, wait_secs)?;
        let (claim, built) =
            match self.claim_and_build(plan, (id, &handle), &lease, branch.as_deref()) {
                Ok(done) => done,
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
            self.ledger_path(&path),
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
            self.note_steal(id, prev, &holder, steal.unwrap_or_default())?;
        }
        let mut warnings = Vec::new();
        warnings.extend(claim);
        if lease.scope.is_empty() {
            warnings.push(format!(
                "{handle} has an empty scope; SCOPE001 will flag every changed file"
            ));
        }
        warnings.extend(frob_lease::unmatched::scope_warnings(
            self.ledger.repo(),
            id,
            &lease.scope,
            &view.ticket.front.labels,
        ));
        if !built.conflicts.is_empty() {
            warnings.push(format!(
                "merging the base left {} conflicted path(s); resolve them in {}",
                built.conflicts.len(),
                Shown::of(&path)
            ));
        }
        let already = !fresh && stolen_from.is_none() && !built.created && applied.already;
        tracing::info!(ticket = %id, path = %Shown::of(&path), already, created = built.created, "ticket started");
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

    /// Record on the ticket that `holder` stole its lease from `prev`.
    fn note_steal(
        &self,
        id: TicketId,
        prev: &Holder,
        holder: &Holder,
        why: &str,
    ) -> Result<(), WorktreeError> {
        let note = format!(
            "lease stolen from {} in {} by {} in {}: {why}",
            prev.actor,
            self.ledger_path(&prev.worktree),
            holder.actor,
            self.ledger_path(&holder.worktree),
        );
        self.ledger.comment(id, CommentSubtype::Note, &note)?;
        Ok(())
    }

    /// Publish the claim, then build the worktree; the caller rolls the lease back on error.
    fn claim_and_build(
        &self,
        plan: &Plan,
        (id, handle): (TicketId, &str),
        lease: &Lease,
        branch: Option<&str>,
    ) -> Result<(Option<String>, Built), WorktreeError> {
        let claim = self.claim(plan, handle, lease, branch)?;
        let built = self.build(plan, id, handle, lease, branch)?;
        Ok((claim, built))
    }

    /// The cycle gates for a ticket taking a fresh slot: no overdue cycle, and inside the active one (or started `unplanned`).
    fn cycle_gates(
        &self,
        taking: (TicketId, frob_ledger::model::Class, &str),
        sprint_gate: bool,
        unplanned: Option<&str>,
    ) -> Result<(), WorktreeError> {
        let (_, class, handle) = taking;
        crate::cycle_gate::check_overdue(self.ledger, class, handle)?;
        crate::cycle_gate::check_sprint(self.ledger, sprint_gate, taking, unplanned)
    }

    /// The current checkout when it is this ticket's own linked worktree and the ticket is in progress with no live lease.
    ///
    /// That is a resumed run whose lease expired: `work` re-leases it here (the
    /// inferred heartbeat of D105). Acquiring still refuses when another holder
    /// leased an overlapping scope since, so a steal is never renewed across.
    fn resumed_worktree(
        &self,
        plan: &Plan,
        category: Category,
        handle: &str,
        leased: bool,
    ) -> Option<PathBuf> {
        if leased || category != Category::InProgress || !matches!(plan, Plan::Work { .. }) {
            return None;
        }
        let repo = self.ledger.repo();
        let here = repo.work_dir()?;
        let branch = format!("ticket/{}", handle.trim_start_matches('~'));
        let own =
            repo.is_linked_worktree() && repo.current_branch().ok()?.as_deref() == Some(&branch);
        tracing::debug!(handle, here = %Shown::of(here), own, "work: resumed worktree check");
        own.then(|| clean(here))
    }

    /// [`Workspace::take`], queueing as a fair waiter for up to `wait_secs` while an overlapping lease or earlier waiter blocks (frob:ticket 01M41ZRNYEWRY4V2MXT3WMXBBJ).
    fn take_waiting(
        &self,
        taking: crate::wip::Taking<'_>,
        needs_slot: bool,
        (holder, scope): (&Holder, &[String]),
        steal: Option<&str>,
        wait_secs: u64,
    ) -> Result<(Lease, bool, Option<Holder>), WorktreeError> {
        let id = taking.id;
        let deadline = std::time::Instant::now() + Duration::from_secs(wait_secs);
        let cap = Duration::from_secs(self.leases.config().waiter_ttl_secs.max(3) / 3)
            .min(Duration::from_secs(2));
        let mut pause = Duration::from_millis(50);
        let mut queued = false;
        let result = loop {
            let taken = self.take(taking, needs_slot, holder, scope, steal);
            let blocked = match &taken {
                Err(WorktreeError::Refused(r)) => {
                    r.code == "E-LEASE-QUEUED"
                        || (r.code == "E-LEASE-HELD" && !r.message.contains(SAME_TICKET))
                }
                _ => false,
            };
            if !blocked || wait_secs == 0 || std::time::Instant::now() >= deadline {
                break taken;
            }
            if let Err(e) = self.leases.enqueue(id, holder, scope) {
                break Err(e.into());
            }
            if !queued {
                tracing::info!(ticket = %id, wait_secs, "queued for lease");
                queued = true;
            }
            std::thread::sleep(
                pause.min(deadline.saturating_duration_since(std::time::Instant::now())),
            );
            pause = (pause * 2).min(cap);
        };
        if queued && let Err(e) = self.leases.dequeue(id) {
            tracing::warn!(ticket = %id, error = %e, "leaving the wait queue failed");
        }
        result
    }

    /// Acquire the lease (or steal it): the lease, whether it is new, and the previous holder when stolen.
    ///
    /// The WIP count runs inside the lease-store lock (when `needs_slot`), so it
    /// and the lease write cannot interleave with another `work`.
    fn take(
        &self,
        taking: crate::wip::Taking<'_>,
        needs_slot: bool,
        holder: &Holder,
        scope: &[String],
        steal: Option<&str>,
    ) -> Result<(Lease, bool, Option<Holder>), WorktreeError> {
        let (id, handle) = (taking.id, taking.handle);
        let limits = crate::wip::Limits {
            repo: self.leases.repo_limit(),
            expedite_max: self.leases.expedite_max(),
        };
        let admit = |live: &[Lease]| {
            if needs_slot {
                crate::wip::check(self.ledger, live, limits, taking)
            } else {
                Ok(())
            }
        };
        match self.leases.acquire_admitting(id, holder, scope, admit) {
            Ok(a) => Ok((a.lease, !a.already, None)),
            Err(WorktreeError::Lease(LeaseError::Held { ticket, .. }))
                if steal.is_some() && ticket == id =>
            {
                let reason = steal.unwrap_or_default();
                let s = self.leases.steal(id, holder, reason)?;
                Ok((s.lease, false, Some(s.previous)))
            }
            Err(WorktreeError::Lease(e)) => Err(held_refusal(e, id, handle)),
            Err(e) => Err(e),
        }
    }

    /// Publish the claim (create-only push of the ticket branch at the base tip) before a fresh worktree is made.
    ///
    /// Nothing is pushed for `start`, for an existing worktree, or without a remote.
    // frob:ticket 01M5CW04QCRZ860BZMT46BECG2
    fn claim(
        &self,
        plan: &Plan,
        handle: &str,
        lease: &Lease,
        branch: Option<&str>,
    ) -> Result<Option<String>, WorktreeError> {
        let (Plan::Work { .. }, Some(branch)) = (plan, branch) else {
            return Ok(None);
        };
        if lease.holder.worktree.join(".git").exists() {
            return Ok(None);
        }
        let base = base_branch(self.ledger);
        let published = crate::claim::publish(self.ledger.repo(), branch, &base)?;
        if let Publication::Lost { tip } = &published {
            return Err(WorktreeError::Refused(
                Refusal::new(
                    E_CLAIM_LOST,
                    RefusalClass::GuardNeedsAction,
                    format!("{handle} is already claimed: {branch} exists on the remote at {tip}"),
                )
                .with_remedy(format!(
                    "pick another ticket; if the claim is yours from another clone, fetch {branch} and resume there"
                )),
            ));
        }
        Ok(match published {
            Publication::Unpublished(why) => Some(format!(
                "{W_CLAIM_UNPUBLISHED}: {handle} is claimed here only; others may take it until a sync publishes {branch} ({why})"
            )),
            _ => None,
        })
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
                    WorktreeError::Config(format!("creating {}: {e}", Shown::of(parent)))
                })?;
            }
            repo.worktree_add(path, branch, &base)?;
            // frob:ticket 01M4MNBNM0WGTXGH93PEV48F78
            let aged = normalize_mtimes(repo, path);
            // frob:ticket 01M4S28S5N358QCYR9A4XM1NC0
            share_build_dir(repo.common_dir(), path);
            // frob:ticket 01M4DPJJW8D3KXZVTEN5D4WN5G
            seed_caches(&self.primary_root());
            tracing::info!(ticket = %id, handle, path = %Shown::of(path), branch, base = %base, aged, "worktree created");
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
        resumed: Option<&Path>,
    ) -> (PathBuf, Option<String>) {
        match plan {
            Plan::Start { cwd } => (cwd.clone(), None),
            Plan::Work { override_path } => {
                let name = handle.trim_start_matches('~');
                let path = match override_path {
                    Some(p) if p.is_absolute() => clean(p),
                    Some(p) => clean(&self.cwd().join(p)),
                    None if let Some(here) = resumed => clean(here),
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
                    .map_or_else(|| name.to_owned(), crate::pathtext::name_text);
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

    // frob:ticket 01M41PM9TCJ8MJQREJ733PZ67A
    /// `path` as a ledger event may record it: relative to the repository's parent directory, never absolute.
    ///
    /// A path outside that directory keeps only its last two components, so no
    /// home directory or user name reaches a pushed ledger.
    pub fn ledger_path(&self, path: &Path) -> String {
        let primary = self.primary_root();
        let base = primary.parent().unwrap_or(&primary);
        ledger_relative(path, base)
    }

    fn primary_root(&self) -> PathBuf {
        primary_root(self.ledger)
    }

    fn default_path(&self, name: &str) -> PathBuf {
        worktree_parent(&self.primary_root(), self.config).join(name)
    }
}

// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29
/// The primary checkout of the repository behind `ledger`: the first worktree git lists, else the current directory.
pub fn primary_root(ledger: &Ledger) -> PathBuf {
    let repo = ledger.repo();
    repo.list_worktrees()
        .ok()
        .and_then(|w| w.into_iter().next().map(|i| i.path))
        .or_else(|| repo.work_dir().map(Path::to_path_buf))
        .unwrap_or_else(|| PathBuf::from("."))
}

// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29
/// The directory `[worktree] dir` names for the primary checkout `primary`, cleaned of `.` and `..`.
pub fn worktree_parent(primary: &Path, config: &WorktreeConfig) -> PathBuf {
    let repo_name = primary
        .file_name()
        .map_or_else(|| "repo".to_owned(), crate::pathtext::name_text);
    let dir = PathBuf::from(config.dir.replace("{repo}", &repo_name));
    let parent = if dir.is_absolute() {
        dir
    } else {
        primary.join(dir)
    };
    clean(&parent)
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
    if let LeaseError::Queued { waiter, .. } = &e {
        let remedy = format!(
            "ticket {waiter} is queued first for this scope; rerun with `frob work {handle} --wait <secs>` to queue behind it"
        );
        return match e.to_refusal() {
            Some(r) => WorktreeError::Refused(r.with_remedy(remedy)),
            None => e.into(),
        };
    }
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

/// `path` relative to `base` with `/` separators; outside `base`, its last two components.
// frob:ticket 01M41PM9TCJ8MJQREJ733PZ67A
fn ledger_relative(path: &Path, base: &Path) -> String {
    let join = |p: &Path| {
        p.components()
            .filter_map(|c| match c {
                Component::Normal(n) => Some(crate::pathtext::name_text(n)),
                _ => None,
            })
            .collect::<Vec<_>>()
            .join("/")
    };
    if let Ok(rel) = path.strip_prefix(base) {
        return join(rel);
    }
    let names: Vec<String> = join(path).split('/').map(str::to_owned).collect();
    let keep = names.len().saturating_sub(2);
    names[keep..].join("/")
}

/// Set the mtime of every tracked file of the checkout at `root` that is newer than its HEAD commit back to the commit time; returns how many files were aged.
///
/// Cargo freshness compares source mtimes with the build's dep-info, so a checkout made after the last
/// build of the same commit would otherwise recompile every workspace crate. Call it right after the
/// checkout is created, before anything edits it: files changed later keep a newer mtime and rebuild.
/// Best effort: any failure leaves mtimes as they are and returns the count so far (frob:ticket 01M4MNBNM0WGTXGH93PEV48F78).
pub fn normalize_mtimes(repo: &Repo, root: &Path) -> usize {
    let Some(commit_secs) = git_out(repo, root, &["log", "-1", "--format=%ct", "HEAD"])
        .and_then(|t| t.trim().parse::<u64>().ok())
    else {
        tracing::debug!(root = %Shown::of(root), "no commit time; mtimes left alone");
        return 0;
    };
    let Some(listing) = git_out(repo, root, &["ls-files", "-z"]) else {
        return 0;
    };
    let when = std::time::UNIX_EPOCH + std::time::Duration::from_secs(commit_secs);
    let mut aged = 0;
    for rel in listing.split('\0').filter(|r| !r.is_empty()) {
        let file = root.join(rel);
        let Ok(meta) = std::fs::symlink_metadata(&file) else {
            continue;
        };
        if !meta.is_file() || meta.modified().is_ok_and(|m| m <= when) {
            continue;
        }
        // Windows needs write access to set times (a read-only handle is refused); Unix does not, so a
        // read-only file falls back to the plain open.
        if std::fs::OpenOptions::new()
            .write(true)
            .open(&file)
            .or_else(|_| std::fs::File::open(&file))
            .and_then(|f| f.set_modified(when))
            .is_ok()
        {
            aged += 1;
        }
    }
    aged
}

/// Stdout of `git <args>` in `cwd` through the repository's runner, or `None` when it fails.
fn git_out(repo: &Repo, cwd: &Path, args: &[&str]) -> Option<String> {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: Some(cwd.to_path_buf()),
        env: Vec::new(),
        timeout: std::time::Duration::from_secs(60),
        capture: true,
    };
    let out = repo.runner().run(&spec).ok()?;
    (out.status == Outcome::Exited(0)).then_some(out.stdout)
}

/// State directories whose shared cache a new worktree is seeded for.
const SEEDED_STATE_DIRS: [&str; 2] = [".frob", ".grimble"];

/// Seed each product's repository-shared cache from the primary checkout's own cache when the shared one does not exist yet.
///
/// Best effort: failures are logged by `gob_cache::seed_shared` and the checks run cold.
// frob:ticket 01M4DPJJW8D3KXZVTEN5D4WN5G
pub fn seed_caches(primary: &Path) {
    for state_dir in SEEDED_STATE_DIRS {
        let outcome = gob_cache::seed_shared(primary, state_dir);
        tracing::debug!(state_dir, ?outcome, "worktree cache seeding");
    }
}

/// Directory (under `<common>/frob/`) of the cargo target directory every land checkout and ticket worktree shares.
pub const SHARED_TARGET_DIR: &str = "land-target";

/// Point `checkout`'s `target/` at the repository-shared land target directory when it has none.
///
/// Every land checkout (the ticket worktree and the persistent base checkout) then reuses the
/// registry dependency builds of every earlier land instead of compiling from an empty
/// directory (measured: 45-200 s per cold pass, ~TSK0M4Y, ~8J3BE8W). An existing `target`
/// (a real directory or a link) is left alone. Failures are logged and the checks run cold.
// frob:ticket 01M4D6NFCDSW5E4FD9X8J3BE8W
// frob:ticket 01M4S28S5N358QCYR9A4XM1NC0
// frob:ticket 01M4H8NECMX7XBS1J6FDWRJEZV
pub fn share_build_dir(common: &Path, checkout: &Path) {
    let link = checkout.join("target");
    if let Ok(meta) = std::fs::symlink_metadata(&link) {
        if meta.file_type().is_symlink() && std::fs::metadata(&link).is_err() {
            tracing::warn!(link = %Shown::of(&link), "dangling build directory link; repairing");
            if let Err(e) = std::fs::remove_file(&link) {
                tracing::warn!(error = %e, "dangling link not removed; cargo stages run cold");
                return;
            }
        } else {
            tracing::debug!(link = %Shown::of(&link), "checkout already has a build directory");
            return;
        }
    }
    let shared = common.join("frob").join(SHARED_TARGET_DIR);
    if let Err(e) = std::fs::create_dir_all(&shared) {
        tracing::warn!(error = %e, dir = %Shown::of(&shared), "shared build directory not created; cargo stages run cold");
        return;
    }
    // Canonical and absolute: `common` may be spelled through a worktree's git dir
    // (`.git/worktrees/<T>/../..`), which dangles once that worktree is removed.
    let shared = match gob_exec::canonical(&shared) {
        Ok(p) => p,
        Err(e) => {
            tracing::warn!(error = %e, dir = %Shown::of(&shared), "shared build directory not canonicalized; cargo stages run cold");
            return;
        }
    };
    exclude_target(common);
    #[cfg(unix)]
    match std::os::unix::fs::symlink(&shared, &link) {
        Ok(()) => {
            tracing::info!(shared = %Shown::of(&shared), checkout = %Shown::of(checkout), "checkout shares the land build directory");
        }
        Err(e) => {
            tracing::warn!(error = %e, "build directory not shared; cargo stages run cold");
        }
    }
    #[cfg(not(unix))]
    tracing::debug!(shared = %Shown::of(&shared), checkout = %Shown::of(checkout), "build directory sharing is unix-only");
}

/// Make git ignore a `/target` entry of any kind: the `target/` pattern of a `.gitignore` matches
/// directories only, so the shared-build symlink would show as an untracked file (and as a SCOPE001 target).
fn exclude_target(common: &Path) {
    let path = common.join("info").join("exclude");
    let text = std::fs::read_to_string(&path).unwrap_or_default();
    if text.lines().any(|l| l.trim() == "/target") {
        return;
    }
    let mut next = text;
    if !next.is_empty() && !next.ends_with('\n') {
        next.push('\n');
    }
    next.push_str("/target\n");
    let result =
        std::fs::create_dir_all(common.join("info")).and_then(|()| std::fs::write(&path, next));
    match result {
        Ok(()) => {
            tracing::info!(path = %Shown::of(&path), "excluded /target for the shared build link");
        }
        Err(e) => tracing::warn!(path = %Shown::of(&path), error = %e, "could not exclude /target"),
    }
}
