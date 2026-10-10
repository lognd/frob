//! The land transaction: preconditions, then the locked publish (tickets.md section 10, D25).
//!
//! Order: resolve and vet the lease, check the worktree is the holder's and
//! clean, run the close guards (evidence, criteria, changelog: ledger and
//! worktree reads only, so a refusal such as `E-DONE-CRITERIA-UNBOUND` comes in
//! seconds), merge the base into the ticket branch (refusing on conflicts), run
//! the ticket-scoped check, then under the land lock
//! fast-forward the base branch, write the `land` event, close the ticket,
//! release the lease and remove the worktree. A dry run stops after the
//! preconditions and prints the plan.
//!
//! The base branch is advanced by spawning git through `gob-exec`:
//! `git merge --ff-only <oid>` in the checkout that has the base checked out
//! (git then updates that index and worktree itself), or
//! `git update-ref <ref> <new> <old>` (compare-and-swap) when no checkout
//! has it. `gob-git` has no ref-update or worktree-removal API yet.

use std::collections::BTreeSet;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use frob_check::CheckOptions;
use frob_evidence::{DoneGuard, EvidenceGuard, Workspace};
use frob_lease::{Lease, LeaseStore};
use frob_ledger::event::{CommentData, EventBody};
use frob_ledger::guards::{CloseContext, CloseGuard, default_close_guards};
use frob_ledger::model::Category;
use frob_ledger::model::CommentSubtype;
use frob_ledger::ops::TicketView;
use frob_ledger::{Ledger, RefMode, TicketId};
use gob_diagnostics::{Refusal, RefusalClass};
use gob_git::{MergeOutcome, Oid, Repo, StatusOptions, TreeRef};

use crate::base_ci;
use crate::error::{LandError, needs_action};
use crate::events::{LandEvent, append_land};
use crate::git::git;
use crate::lock::LandLock;
use crate::lockfile;
use crate::plan::{LandOptions, LandOutcome, PlanInputs, RetryPolicy, digest, steps};
use crate::ratchet::{self, Ratchet};
use gob_time::Clock;
use std::sync::Arc;

/// Stable code of the refusal when the base moved during the land.
const CODE_STALE: &str = "E-LAND-STALE";

/// How many dirty paths a refusal message lists before summarising.
const LIST_CAP: usize = 10;

/// Land the ticket named by `opts` from the repository containing `root`.
///
/// # Errors
///
/// A [`LandError::Refused`] per failed precondition (`E-LAND-NOT-LEASED`,
/// `E-LAND-WRONG-WORKTREE`, `E-LAND-DIRTY`, `E-LAND-CONFLICT`,
/// `E-LAND-CHECK-RED`, the evidence guard's code, `E-LAND-LOCKED`,
/// `E-LAND-STALE`), plus ledger, lease, git and I/O failures.
pub fn land(
    root: &Path,
    opts: &LandOptions,
    clock: &Arc<dyn Clock>,
) -> Result<LandOutcome, LandError> {
    let repo = Repo::discover(root).map_err(|e| LandError::Config(e.to_string()))?;
    let cwd_root = work_dir(&repo)?;
    let here = Workspace::open(&cwd_root, clock.clone())?;
    let (leases, _) = frob_lease::open_store_from_file(&cwd_root, clock.clone())?;
    let id = resolve(&here.ledger, &leases, &cwd_root, opts.handle.as_deref())?;
    let view = here.ledger.show(id)?;
    let handle = view.summary.handle.clone();
    let base = frob_worktree::work::base_branch(&here.ledger);
    tracing::info!(ticket = %id, handle = %handle, base = %base, dry_run = opts.dry_run, "land started");

    if view.summary.category == Category::Done {
        tracing::info!(ticket = %id, "ticket already done; land is a no-op");
        return Ok(LandOutcome {
            already: true,
            outcome: view.ticket.front.outcome,
            ..empty_outcome(id, &handle, &base, opts)
        });
    }
    let ready = prepare(repo, &cwd_root, here, &leases, &view, &base, opts)?;
    if opts.dry_run {
        return ready.planned(opts);
    }
    ready.publish(&leases, opts)
}

/// Everything the preconditions established, ready to plan or publish.
struct Ready {
    repo: Repo,
    wt: Repo,
    wt_path: PathBuf,
    primary: PathBuf,
    id: TicketId,
    handle: String,
    base: String,
    branch: String,
    base_merged: bool,
    /// The ticket's affected cone at the checked tree, when the check reported one.
    cone: Option<BTreeSet<String>>,
    /// The ticket's scope globs, for telling whether a file the base added joins the cone.
    scope: Vec<String>,
    ci_override: Option<String>,
    site: Workspace,
    evidence: EvidenceGuard,
    done: DoneGuard,
    out: LandOutcome,
}

// frob:ticket 01M4FG552GZ9FMB000B76AS8XH
/// True when every path that changed from `fork` to `base_oid` lies under the ledger directory `dir` (trunk-mode ticket commits).
fn ledger_only_ahead(
    wt: &Repo,
    fork: Option<Oid>,
    base_oid: Oid,
    dir: &str,
) -> Result<bool, LandError> {
    let Some(fork) = fork else {
        return Ok(false);
    };
    let prefix = format!("{}/", dir.trim_end_matches('/'));
    let changed = wt.diff_names(&TreeRef::Oid(fork), &TreeRef::Oid(base_oid))?;
    Ok(changed.iter().all(|c| c.path.starts_with(&prefix)))
}

/// Check every precondition (merging the base into the ticket branch unless dry-running).
fn prepare(
    repo: Repo,
    cwd_root: &Path,
    here: Workspace,
    leases: &LeaseStore,
    view: &TicketView,
    base: &str,
    opts: &LandOptions,
) -> Result<Ready, LandError> {
    let clock = here.ledger.clock().clone();
    let id = view.ticket.front.id;
    let handle = view.summary.handle.clone();
    let lease = held_lease(&repo, leases, &here.ledger, view, id, &handle, cwd_root)?;
    let wt_path = lease.holder.worktree.clone();
    let primary = primary_root(&repo)?;
    check_worktree(&repo, cwd_root, &wt_path, &handle)?;
    let wt = Repo::discover(&wt_path).map_err(|e| LandError::Config(e.to_string()))?;
    let branch = ticket_branch(&wt, base, &wt_path, &handle)?;
    ensure_clean(&wt, &wt_path)?;

    // frob:ticket 01M4FJ57NER0WMX4FPNY7E721R
    // The close guards read only the ledger and the worktree, so they run before any merge or check:
    // an unbound criterion refuses in seconds, not after a cold build.
    let site = if here.ledger.config().mode == RefMode::Branch {
        Workspace::open(&wt_path, clock.clone())?
    } else if primary == cwd_root {
        here
    } else {
        Workspace::open(&primary, clock.clone())?
    };
    let mut evidence = EvidenceGuard::for_ticket(&site.ledger, &site.store, id)?;
    let mut done = DoneGuard::for_ticket(&site.ledger, id, &wt_path)?;
    if let Some(reason) = &opts.no_evidence_reason {
        evidence = evidence.allow_bypass(reason.clone());
        done = done.allow_bypass(reason.clone());
    }
    if let Some(reason) = &opts.no_changelog_reason {
        done = done.allow_no_changelog(reason.clone());
    }
    run_guards(view, &handle, &evidence, &done, opts)?;

    let base_oid = wt.rev_parse(&base_ref(base)).map_err(|_| {
        needs_action(
            "E-LAND-NO-BASE",
            format!("base branch `{base}` does not exist"),
            "set [tickets] ref to an existing branch in frob.toml",
        )
    })?;
    let ci_gate = base_ci::gate(
        &wt,
        &wt_path,
        base,
        opts.ci_reader.as_deref(),
        opts.override_base_ci.as_deref(),
    )?;
    let mut base_merge = None;
    let fork = wt.merge_base(&base_ref(base), &branch)?;
    let mut base_merged = fork == Some(base_oid);
    if !base_merged && !opts.dry_run {
        base_merge = Some(merge_base_in(&wt, &wt_path, base, &handle)?);
        base_merged = true;
    } else if base_merged {
        base_merge = Some("up-to-date".to_owned());
    } else if ledger_only_ahead(&wt, fork, base_oid, &site.ledger.config().dir)? {
        // frob:ticket 01M4FG552GZ9FMB000B76AS8XH
        // Trunk-mode ticket verbs commit to the base all the time; those commits carry no code.
        tracing::info!(
            base,
            "dry run: the base is ahead only by ledger commits; treated as merged"
        );
        base_merge = Some("up-to-date (the base moved only by ledger commits)".to_owned());
        base_merged = true;
    }
    let mut warnings = ci_gate.warnings;
    let mut ratchet = Ratchet::default();
    if base_merged {
        ratchet = verify_check(&wt, &wt_path, &site.ledger, &handle, base, opts)?;
    } else {
        // A dry run leaves the base unmerged, so the ticket-scoped diff would
        // include the base's own changes; the real land merges first.
        warnings.push(format!(
            "check skipped: {base} is not merged into {branch} yet and a dry run does not merge it"
        ));
    }

    let mut done_view = view.ticket.clone();
    done_view.front.outcome = Some(opts.outcome);
    warnings.extend(done.warnings(&done_view));
    let out = LandOutcome {
        branch: Some(branch.clone()),
        worktree: Some(wt_path.clone()),
        base_merge,
        warnings,
        pre_existing: ratchet.pre_existing,
        resolved: ratchet.resolved,
        ..empty_outcome(id, &handle, base, opts)
    };
    let cone = ratchet.cone;
    Ok(Ready {
        repo,
        wt,
        wt_path,
        primary,
        id,
        handle,
        base: base.to_owned(),
        branch,
        base_merged,
        cone,
        scope: view.ticket.front.scope.clone(),
        ci_override: ci_gate.override_note,
        site,
        evidence,
        done,
        out,
    })
}

impl Ready {
    /// The dry-run result: the ordered plan and its digest, nothing changed.
    fn planned(mut self, opts: &LandOptions) -> Result<LandOutcome, LandError> {
        let head = self.wt.rev_parse(&self.branch)?.to_string();
        let base_oid = self.wt.rev_parse(&base_ref(&self.base))?.to_string();
        self.out.plan = steps(&PlanInputs {
            id: self.id,
            handle: &self.handle,
            base: &self.base,
            branch: &self.branch,
            worktree: &self.wt_path,
            base_merged: self.base_merged,
            outcome: opts.outcome,
            push: opts.push,
            keep_worktree: opts.keep_worktree,
        });
        self.out.digest = Some(digest(self.id, &head, &base_oid));
        tracing::info!(ticket = %self.id, "land dry run planned");
        Ok(self.out)
    }

    /// Take the lock, advance the base, record and close, release the lease and clean up.
    fn publish(
        mut self,
        leases: &LeaseStore,
        opts: &LandOptions,
    ) -> Result<LandOutcome, LandError> {
        let on_branch = self.site.ledger.config().mode == RefMode::Branch;
        let actor = self.site.ledger.actor()?;
        let started = Instant::now();
        let _lock = LandLock::acquire(
            self.repo.common_dir(),
            Duration::from_secs(opts.wait_secs),
            &format!("{actor} landing {}", self.handle),
        )?;
        let ctx = Publish {
            repo: &self.repo,
            wt: &self.wt,
            primary: &self.primary,
            base: &self.base,
            branch: &self.branch,
            handle: &self.handle,
        };
        let site = &self.site;
        let (id, base, branch) = (self.id, &self.base, &self.branch);
        let (evidence, done) = (&self.evidence, &self.done);
        let ci_override = self.ci_override.as_deref();
        let retrying = opts.wait_secs > 0;
        let budget = opts
            .retry
            .budget
            .unwrap_or_else(|| Duration::from_secs(opts.wait_secs));
        let mut cone = self.cone.clone();
        let mut attempt = 0_u32;
        let oid = loop {
            attempt += 1;
            if let Some(hook) = &opts.retry.before_attempt {
                hook(attempt);
            }
            let advanced = ctx.advance(on_branch, || {
                ledger_step(
                    &site.ledger,
                    id,
                    (evidence, done, ci_override),
                    opts,
                    base,
                    branch,
                    false,
                )
            });
            match advanced {
                Err(LandError::Refused(r)) if retrying && r.code == CODE_STALE => {
                    if let Some(r) = ctx.recover_stale(
                        &site.ledger,
                        opts,
                        (cone.as_ref(), &self.scope),
                        attempt,
                        started,
                        budget,
                    )? {
                        self.out.pre_existing = r.pre_existing;
                        self.out.resolved = r.resolved;
                        cone = r.cone;
                    }
                }
                other => break other?,
            }
        };
        self.out.attempts = attempt;
        self.out.commit = Some(oid.to_string());
        if opts.push {
            self.out.pushed = push_base(&self.repo, &self.base, &mut self.out.warnings);
        }
        if !on_branch && !self.close_after_advance(opts) {
            return Ok(self.out);
        }
        self.out.closed = true;
        self.out.outcome = Some(opts.outcome);
        self.out
            .changelog_exempt
            .clone_from(&opts.no_changelog_reason);
        release(leases, self.id, &actor, &mut self.out.warnings);
        if !opts.keep_worktree && self.wt_path != self.primary {
            self.out.worktree_removed = remove_worktree(
                &self.repo,
                &self.primary,
                &self.wt_path,
                &self.branch,
                &self.base,
                &mut self.out.warnings,
            );
        }
        // frob:ticket 01M424QEMYGC9VZZYX9BZXZK29
        collect_garbage(
            &self.primary,
            leases,
            self.site.ledger.clock().clone(),
            &mut self.out.warnings,
        );
        tracing::info!(ticket = %self.id, commit = %oid, pushed = self.out.pushed, "land complete");
        Ok(self.out)
    }
}

impl Ready {
    /// Record the land and close the ticket after the base advanced (trunk mode); false when that failed.
    ///
    /// Point of no return: the base has already moved, so a failure is a warning,
    /// never an error. The ticket stays open with its lease and worktree so
    /// `frob ticket close` can finish it.
    fn close_after_advance(&mut self, opts: &LandOptions) -> bool {
        let closed = ledger_step(
            &self.site.ledger,
            self.id,
            (&self.evidence, &self.done, self.ci_override.as_deref()),
            opts,
            &self.base,
            &self.branch,
            self.out.pushed,
        );
        let Err(e) = closed else {
            return true;
        };
        tracing::warn!(ticket = %self.id, error = %e, "ledger step failed after the base advanced");
        self.out.warnings.push(format!(
            "landed {} onto {} but recording the close failed: {e}; run `frob ticket close {}`",
            self.branch, self.base, self.handle
        ));
        false
    }
}

// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29
/// Run the throttled garbage-collection pass from the primary checkout once the worktree is gone.
///
/// The land is already done, so nothing here can fail it: every problem, and every
/// worktree the pass kept because it holds unsaved work, becomes a warning. The ledger
/// is opened on the primary checkout, not the removed worktree, so no index is
/// recreated inside a directory that no longer exists. Also sweeps abandoned
/// ratchet base checkouts under the git common dir (`land-base-*`).
fn collect_garbage(
    primary: &Path,
    leases: &LeaseStore,
    clock: Arc<dyn Clock>,
    warnings: &mut Vec<String>,
) {
    let opened = Repo::discover(primary)
        .map_err(|e| e.to_string())
        .and_then(|repo| {
            let ledger_cfg = frob_worktree::ledger_config(primary)?;
            let wt = frob_worktree::WorktreeConfig::load(primary).map_err(|e| e.to_string())?;
            let gc = frob_worktree::GcConfig::load(primary).map_err(|e| e.to_string())?;
            Ok((Ledger::open(repo, ledger_cfg, clock), wt, gc))
        });
    let (ledger, wt, gc) = match opened {
        Ok(o) => o,
        Err(e) => {
            tracing::warn!(error = %e, "gc after land skipped");
            warnings.push(format!("garbage collection skipped: {e}"));
            return;
        }
    };
    let report =
        frob_worktree::gc::glue::run_for(&ledger, leases, &wt, &gc, frob_worktree::gc::Mode::Auto);
    warnings.extend(frob_worktree::gc::glue::notices(&report));
}

/// A blank outcome for `id`; callers fill in what they did.
fn empty_outcome(id: TicketId, handle: &str, base: &str, opts: &LandOptions) -> LandOutcome {
    LandOutcome {
        id,
        handle: handle.to_owned(),
        already: false,
        dry_run: opts.dry_run,
        base: base.to_owned(),
        branch: None,
        worktree: None,
        commit: None,
        base_merge: None,
        pushed: false,
        closed: false,
        outcome: None,
        worktree_removed: false,
        digest: None,
        plan: Vec::new(),
        attempts: 0,
        warnings: Vec::new(),
        pre_existing: Vec::new(),
        resolved: Vec::new(),
        changelog_exempt: None,
    }
}

/// The work tree root of `repo`.
fn work_dir(repo: &Repo) -> Result<PathBuf, LandError> {
    repo.work_dir()
        .map(Path::to_path_buf)
        .ok_or_else(|| LandError::Config("not inside a git work tree".to_owned()))
}

/// The primary checkout: the first entry of the worktree list.
fn primary_root(repo: &Repo) -> Result<PathBuf, LandError> {
    Ok(repo
        .list_worktrees()?
        .into_iter()
        .next()
        .map(|w| w.path)
        .unwrap_or(work_dir(repo)?))
}

/// `path` resolved through symlinks when it exists, so equal places compare equal.
fn canon(path: &Path) -> PathBuf {
    gob_exec::canonical(path).unwrap_or_else(|_| path.to_path_buf())
}

/// The ticket to land: the given reference, else the one leased by `cwd_root`.
fn resolve(
    ledger: &Ledger,
    leases: &LeaseStore,
    cwd_root: &Path,
    handle: Option<&str>,
) -> Result<TicketId, LandError> {
    if let Some(h) = handle {
        return Ok(ledger.resolve(h)?);
    }
    let here = canon(cwd_root);
    leases
        .live_snapshot()?
        .into_iter()
        .find(|l| canon(&l.holder.worktree) == here)
        .map(|l| l.ticket)
        .ok_or_else(|| {
            needs_action(
                "E-LAND-NOT-LEASED",
                format!("no ticket is leased by {}", cwd_root.display()),
                "frob land <ticket>",
            )
        })
}

/// The live lease of an in-progress ticket held by this actor.
fn held_lease(
    repo: &Repo,
    leases: &LeaseStore,
    ledger: &Ledger,
    view: &TicketView,
    id: TicketId,
    handle: &str,
    cwd_root: &Path,
) -> Result<Lease, LandError> {
    let not_leased =
        |why: String| needs_action("E-LAND-NOT-LEASED", why, format!("frob work {handle}"));
    if view.summary.category != Category::InProgress {
        return Err(not_leased(format!(
            "{handle} is {}, not in progress",
            view.summary.category
        )));
    }
    let actor = ledger.actor()?;
    let lease = match leases.live_lease(id)? {
        Some(l) => l,
        None => reclaim_expired(repo, leases, view, id, &actor, cwd_root).map_err(|e| {
            not_leased(format!(
                "{handle} has no live lease and it cannot be renewed: {e}"
            ))
        })?,
    };
    if lease.holder.actor != actor {
        return Err(not_leased(format!(
            "{handle} is leased by {}, not {actor}",
            lease.holder
        )));
    }
    Ok(lease)
}

/// The linked worktree checked out on the ticket's own branch (`ticket/<handle>`), if one exists.
///
/// An expired lease file is pruned by any later lease verb, so the holder's
/// worktree is recovered from the branch rather than from the cwd (which is
/// the primary when landing from the root).
fn ticket_worktree(repo: &Repo, view: &TicketView) -> Option<PathBuf> {
    let branch = format!("ticket/{}", view.summary.handle.trim_start_matches('~'));
    let found = repo
        .list_worktrees()
        .ok()?
        .into_iter()
        .skip(1)
        .find(|w| w.branch.as_deref() == Some(branch.as_str()))
        .map(|w| w.path);
    tracing::debug!(%branch, found = ?found, "land: ticket branch worktree lookup");
    found
}

/// Renew a lease that expired during a long run, provided nothing else took the ticket or its scope since.
///
/// The old holder (this actor's recorded worktree, else the current one) re-takes
/// the scope under the lease lock; an overlapping or foreign live lease refuses.
fn reclaim_expired(
    repo: &Repo,
    leases: &LeaseStore,
    view: &TicketView,
    id: TicketId,
    actor: &str,
    cwd_root: &Path,
) -> Result<Lease, frob_lease::LeaseError> {
    let recorded = leases.recorded_lease(id)?;
    let holder = match recorded {
        Some(l) if l.holder.actor == actor => l.holder,
        Some(l) => return Err(frob_lease::LeaseError::NotHeld { ticket: l.ticket }),
        None => frob_lease::Holder {
            actor: actor.to_owned(),
            worktree: ticket_worktree(repo, view).unwrap_or_else(|| cwd_root.to_path_buf()),
        },
    };
    tracing::info!(ticket = %id, %holder, "land: lease expired, trying to renew");
    leases.reclaim(id, &holder, &view.ticket.front.scope)
}

/// Refuse landing a worktree other than the holder's: from another linked worktree, or a vanished one.
fn check_worktree(
    repo: &Repo,
    cwd_root: &Path,
    wt_path: &Path,
    handle: &str,
) -> Result<(), LandError> {
    let wrong = |why: String| {
        needs_action(
            "E-LAND-WRONG-WORKTREE",
            why,
            format!("cd {} && frob land {handle}", wt_path.display()),
        )
    };
    if !wt_path.join(".git").exists() {
        return Err(wrong(format!(
            "the leased worktree {} does not exist",
            wt_path.display()
        )));
    }
    if repo.is_linked_worktree() && canon(cwd_root) != canon(wt_path) {
        return Err(wrong(format!(
            "{handle} is leased to {}, not this worktree ({})",
            wt_path.display(),
            cwd_root.display()
        )));
    }
    Ok(())
}

/// The branch checked out in the holder's worktree; it must not be the base.
fn ticket_branch(wt: &Repo, base: &str, wt_path: &Path, handle: &str) -> Result<String, LandError> {
    let wrong =
        |why: String| needs_action("E-LAND-WRONG-WORKTREE", why, format!("frob work {handle}"));
    match wt.current_branch()? {
        None => Err(wrong(format!("{} has a detached HEAD", wt_path.display()))),
        Some(b) if b == base => Err(wrong(format!(
            "{} is on the base branch {base}; there is nothing to land",
            wt_path.display()
        ))),
        Some(b) => Ok(b),
    }
}

/// Refuse a worktree with uncommitted changes, listing the paths (`.frob/` is frob's own state).
fn ensure_clean(wt: &Repo, wt_path: &Path) -> Result<(), LandError> {
    let mut dirty: Vec<String> = wt
        .status(&StatusOptions::default())?
        .into_iter()
        .map(|e| e.path)
        .filter(|p| !p.starts_with(".frob/"))
        .collect();
    dirty.dedup();
    if dirty.is_empty() {
        return Ok(());
    }
    let more = dirty.len().saturating_sub(LIST_CAP);
    let mut listed = dirty
        .iter()
        .take(LIST_CAP)
        .cloned()
        .collect::<Vec<_>>()
        .join(", ");
    if more > 0 {
        listed = format!("{listed} and {more} more");
    }
    Err(needs_action(
        "E-LAND-DIRTY",
        format!("{} has uncommitted changes: {listed}", wt_path.display()),
        format!(
            "git -C {} add -A && git -C {} commit -m <message>",
            wt_path.display(),
            wt_path.display()
        ),
    ))
}

/// Merge `base` into the ticket branch inside its worktree; conflicts are listed (`E-LAND-CONFLICT`) and the merge aborted.
///
/// Configuration is read from the base's committed `frob.toml` before the merge
/// starts, never from the worktree mid-merge (frob:ticket 01M43FX5KWVP277RX5666MMPM1).
fn merge_base_in(wt: &Repo, wt_path: &Path, base: &str, handle: &str) -> Result<String, LandError> {
    let shared_files = lockfile::committed_shared_files(wt, base)?;
    match wt.merge_branch(wt_path, base)? {
        MergeOutcome::UpToDate => Ok("up-to-date".to_owned()),
        MergeOutcome::FastForward => {
            tracing::info!(base, "base fast-forwarded into the ticket branch");
            Ok("fast-forward".to_owned())
        }
        MergeOutcome::Merged => {
            tracing::info!(base, "base merged into the ticket branch");
            Ok("merged".to_owned())
        }
        // frob:ticket 01M418TM2GZ24YPQE7ECTKE1J4
        MergeOutcome::Conflicts(paths) if lockfile::all_shared(&shared_files, &paths)? => {
            tracing::info!(
                count = paths.len(),
                "base merge conflicts only in shared lockfiles"
            );
            lockfile::resolve(wt, wt_path, base, &paths)
        }
        MergeOutcome::Conflicts(paths) => {
            let abort = git(wt, wt_path, &["merge", "--abort"])?;
            tracing::warn!(
                count = paths.len(),
                aborted = abort.ok(),
                "base merge conflicted"
            );
            Err(needs_action(
                "E-LAND-CONFLICT",
                format!("merging {base} conflicts in: {}", paths.join(", ")),
                format!(
                    "git -C {} merge {base}, resolve, commit, then frob land {handle}",
                    wt_path.display()
                ),
            ))
        }
    }
}

// frob:ticket 01M4GRW6NH23YPTSAQED5ZJPVH
/// True when a base move `changes` can alter the ticket's verdict: it touches a non-ledger path in `cone` or under the ticket's `scope` globs (any non-ledger path when there is no cone).
fn touches_cone(
    changes: &[gob_git::ChangedPath],
    cone: Option<&BTreeSet<String>>,
    scope: &[String],
    ledger: &frob_ledger::LedgerConfig,
) -> bool {
    // A file the base added under the ticket's scope globs joins the cone at the next check.
    let in_scope = frob_lease::overlap::glob_set(scope).ok();
    changes.iter().any(|c| {
        !ledger.is_ledger_path(&c.path)
            && cone.is_none_or(|files| {
                files.contains(&c.path) || in_scope.as_ref().is_none_or(|set| set.is_match(&c.path))
            })
    })
}

/// Run the checks in the worktree; refuse on a finding at the configured `fail_on` that is new relative to the base tip.
///
/// The ratchet (rules.md section 6) compares like with like: the unscoped
/// check at the head against the unscoped check at the base, so repository
/// level findings such as REL001 match across the two. The ticket-scoped run
/// adds the ticket-only findings (SCOPE001, done rules) that no unscoped run
/// has. Blocking findings already on the base are returned as pre-existing,
/// base findings that are gone as resolved.
fn verify_check(
    wt: &Repo,
    wt_path: &Path,
    ledger: &Ledger,
    handle: &str,
    base: &str,
    opts: &LandOptions,
) -> Result<Ratchet, LandError> {
    // The tool stages (minutes of cargo) run once, in the ticket-scoped run, where they narrow
    // themselves to the stages and cargo packages the scope touches; the unscoped head run only
    // supplies the repository-level findings the ratchet compares like with like, so it skips
    // them and is served mostly from the shared file cache
    // (frob:ticket 01M4D6NFCDSW5E4FD9X8J3BE8W, 01M4GRW6NH23YPTSAQED5ZJPVH).
    ratchet::share_build_dir(wt.common_dir(), wt_path);
    let options = |ticket: Option<&str>| CheckOptions {
        ticket: ticket.map(str::to_owned),
        base: ticket.map(|_| base.to_owned()),
        ledger: Some(ledger.config().clone()),
        clock: Some(ledger.clock().clone()),
        skip_telemetry: true,
        skip_tools: ticket.is_none(),
        changelog_exempt: opts.no_changelog_reason.is_some(),
        ..CheckOptions::default()
    };
    let (scoped, _, cone) = frob_check::run_with_cone(wt_path, &options(Some(handle)))?;
    let head = frob_check::run(wt_path, &options(None))?;
    let base_oid = wt.rev_parse(&base_ref(base))?.to_string();
    let base_set = ratchet::base_findings(wt, wt_path, &base_oid, ledger.config())?;
    let mut verdict = ratchet::verdict(&scoped, &head, &base_set);
    if let Some(cone) = &cone {
        // The scoped run examines only the cone, so a base finding elsewhere was not re-judged.
        verdict
            .resolved
            .retain(|n| n.path.as_deref().is_none_or(|p| cone.contains(p)));
    }
    tracing::info!(
        new = verdict.new.len(),
        pre_existing = verdict.pre_existing.len(),
        resolved = verdict.resolved.len(),
        non_blocking = verdict.non_blocking,
        "land check ratchet"
    );
    if verdict.new.is_empty() {
        return Ok(Ratchet {
            pre_existing: verdict.pre_existing,
            resolved: verdict.resolved,
            cone,
        });
    }
    tracing::warn!(blocking = verdict.new.len(), "land check red");
    Err(refuse(&scoped, &verdict, (handle, base)))
}

/// The `E-LAND-CHECK-RED` refusal naming only the new blocking findings of `verdict`.
fn refuse(
    report: &frob_check::CheckReport,
    verdict: &ratchet::Verdict,
    (handle, base): (&str, &str),
) -> LandError {
    let new = &verdict.new;
    let (non_blocking, pre_existing) = (verdict.non_blocking, verdict.pre_existing.len());
    let listed: Vec<String> = new
        .iter()
        .take(LIST_CAP)
        .map(|n| {
            format!(
                "{} {}: {}",
                n.rule,
                n.path.as_deref().unwrap_or("-"),
                n.message
            )
        })
        .collect();
    let hidden = new.len().saturating_sub(LIST_CAP);
    let mut tail = String::new();
    if hidden > 0 {
        let _ = write!(tail, "; and {hidden} more blocking finding(s)");
    }
    if non_blocking > 0 {
        let _ = write!(tail, "; and {non_blocking} non-blocking findings");
    }
    if pre_existing > 0 {
        let _ = write!(
            tail,
            "; {pre_existing} pre-existing blocking finding(s) on {base} do not block"
        );
    }
    LandError::Refused(
        Refusal::new(
            "E-LAND-CHECK-RED",
            RefusalClass::GuardNeedsAction,
            format!(
                "frob check --ticket {handle} has {} new blocking finding(s) at or above fail_on ({:?}): {}{tail}",
                new.len(),
                report.fail_on,
                listed.join("; ")
            ),
        )
        .with_remedy(format!("frob check --ticket {handle}")),
    )
}

/// Evaluate the same close guards `ticket close` applies, before anything moves.
fn run_guards(
    view: &TicketView,
    handle: &str,
    evidence: &EvidenceGuard,
    done: &DoneGuard,
    opts: &LandOptions,
) -> Result<(), LandError> {
    let defaults = default_close_guards();
    let mut guards: Vec<&dyn CloseGuard> = defaults.iter().map(|g| &**g).collect();
    guards.push(evidence);
    guards.push(done);
    let cx = CloseContext {
        ticket: &view.ticket,
        handle,
        outcome: Some(opts.outcome),
    };
    for g in guards {
        if let Err(f) = g.check(&cx) {
            tracing::info!(guard = g.name(), code = %f.code, "land close guard refused");
            let r = Refusal::new(f.code, RefusalClass::GuardNeedsAction, f.message);
            return Err(LandError::Refused(match f.remedy {
                Some(c) => r.with_remedy(c),
                None => r,
            }));
        }
    }
    Ok(())
}

/// The pieces of the locked publish.
struct Publish<'a> {
    repo: &'a Repo,
    wt: &'a Repo,
    primary: &'a Path,
    base: &'a str,
    branch: &'a str,
    handle: &'a str,
}

impl Publish<'_> {
    /// The retryable `E-LAND-STALE` refusal, naming the attempt count once retries ran out.
    fn stale(&self, gave_up_after: Option<u32>) -> LandError {
        let message = match gave_up_after {
            None => format!("{} moved while landing", self.base),
            Some(n) => format!(
                "{} moved while landing; gave up after {n} attempt(s) because the --wait budget is spent",
                self.base
            ),
        };
        LandError::Refused(
            Refusal::new(CODE_STALE, RefusalClass::GuardRetryByWaiting, message)
                .with_remedy(format!("frob land {} --wait <secs>", self.handle)),
        )
    }

    /// After a stale compare-and-swap (frob:ticket ~VMHTBE7): back off, re-merge the moved base and re-check only if code changed.
    ///
    /// Ledger-only moves, and moves that touch nothing in the ticket's affected
    /// cone, cannot change the check verdict, so the check is skipped unless a
    /// cone path differs between the base the branch contained and the new base
    /// (any non-ledger path when the check reported no cone). Nothing is written before
    /// the compare-and-swap succeeds, so a crash here resumes with `frob land`.
    fn recover_stale(
        &self,
        ledger: &Ledger,
        opts: &LandOptions,
        (cone, scope): (Option<&BTreeSet<String>>, &[String]),
        attempt: u32,
        started: Instant,
        budget: Duration,
    ) -> Result<Option<Ratchet>, LandError> {
        let elapsed = started.elapsed();
        if elapsed >= budget {
            tracing::warn!(attempt, ?elapsed, ?budget, "land retry budget spent");
            return Err(self.stale(Some(attempt)));
        }
        let pause = jitter(&opts.retry, attempt, self.handle).min(budget.saturating_sub(elapsed));
        tracing::info!(
            attempt,
            ?pause,
            base = self.base,
            "base moved while landing; retrying"
        );
        std::thread::sleep(pause);
        let had = self.wt.merge_base(&base_ref(self.base), self.branch)?;
        let wt_path = self
            .wt
            .work_dir()
            .map(Path::to_path_buf)
            .ok_or_else(|| LandError::Config("not inside a git work tree".to_owned()))?;
        let how = merge_base_in(self.wt, &wt_path, self.base, self.handle)?;
        let now = self.wt.rev_parse(&base_ref(self.base))?;
        let code_changed = match had {
            Some(old) if old != now => {
                let changes = self.wt.diff_names(&TreeRef::Oid(old), &TreeRef::Oid(now))?;
                touches_cone(&changes, cone, scope, ledger.config())
            }
            Some(_) => false,
            None => true,
        };
        tracing::info!(attempt, merge = %how, code_changed, "stale base re-merged");
        if code_changed {
            // The base moved, so its fingerprints are recomputed for the new tip (the cache is keyed by oid).
            return verify_check(self.wt, &wt_path, ledger, self.handle, self.base, opts).map(Some);
        }
        Ok(None)
    }

    /// Fast-forward the base branch to the ticket branch tip; `before` runs first in `branch` ref mode.
    ///
    /// In branch ref mode the ledger commits ride on the ticket branch, so
    /// they are written before the tip is read; in trunk mode `before` is not
    /// called (the caller writes them after the base has moved).
    fn advance(
        &self,
        ledger_on_branch: bool,
        before: impl FnOnce() -> Result<(), LandError>,
    ) -> Result<Oid, LandError> {
        let base_oid = self.wt.rev_parse(&base_ref(self.base))?;
        if self.wt.merge_base(&base_ref(self.base), self.branch)? != Some(base_oid) {
            return Err(self.stale(None));
        }
        if ledger_on_branch {
            before()?;
        }
        let checked_out = self
            .repo
            .list_worktrees()?
            .into_iter()
            .find(|w| w.branch.as_deref() == Some(self.base));
        let head = self.wt.rev_parse(self.branch)?;
        if head == base_oid {
            tracing::info!(base = self.base, "base already at the ticket tip");
            return Ok(head);
        }
        let hex = head.to_string();
        let run = if let Some(w) = &checked_out {
            tracing::info!(base = self.base, at = %w.path.display(), "fast-forwarding the checked-out base");
            git(self.repo, &w.path, &["merge", "--ff-only", &hex])?
        } else {
            tracing::info!(
                base = self.base,
                "updating the base ref by compare-and-swap"
            );
            let full = format!("refs/heads/{}", self.base);
            git(
                self.repo,
                self.primary,
                &[
                    "update-ref",
                    "-m",
                    "frob land",
                    &full,
                    &hex,
                    &base_oid.to_string(),
                ],
            )?
        };
        if !run.ok() {
            return Err(LandError::Refused(
                Refusal::new(
                    "E-LAND-ADVANCE",
                    RefusalClass::GuardNeedsAction,
                    format!(
                        "could not advance {} to {}: {}",
                        self.base, self.branch, run.text
                    ),
                )
                .with_remedy(format!(
                    "commit or stash local changes in the checkout of {}, then frob land {}",
                    self.base, self.handle
                )),
            ));
        }
        Ok(head)
    }
}

/// A full-jitter backoff for `attempt`: uniform in zero to the doubling ceiling (clock entropy, no rng dependency).
fn jitter(policy: &RetryPolicy, attempt: u32, salt: &str) -> Duration {
    let ceiling = policy
        .backoff_base
        .saturating_mul(1_u32 << attempt.min(16))
        .min(policy.backoff_max);
    let nanos = gob_time::SystemClock::entropy_nanos();
    let mut h = blake3::Hasher::new();
    h.update(&nanos.to_le_bytes());
    h.update(&attempt.to_le_bytes());
    h.update(salt.as_bytes());
    let bytes = h.finalize();
    let draw = u64::from_le_bytes(bytes.as_bytes()[..8].try_into().expect("8 bytes"));
    let ceil_nanos = u64::try_from(ceiling.as_nanos()).unwrap_or(u64::MAX).max(1);
    Duration::from_nanos(draw % ceil_nanos)
}

/// The full ref name of the base branch: resolved by full name, never by a DWIM short name that a concurrent ref change can make ambiguous or stale.
fn base_ref(base: &str) -> String {
    format!("refs/heads/{base}")
}

/// Record the `land` event, close the ticket through the guards and audit an evidence bypass.
fn ledger_step(
    ledger: &Ledger,
    id: TicketId,
    guards: (&EvidenceGuard, &DoneGuard, Option<&str>),
    opts: &LandOptions,
    base: &str,
    branch: &str,
    pushed: bool,
) -> Result<(), LandError> {
    let commit = ledger
        .repo()
        .rev_parse(&format!("refs/heads/{branch}"))
        .or_else(|_| ledger.repo().rev_parse(&base_ref(base)))?
        .to_string();
    let base_ref = base_ref(base);
    append_land(
        ledger,
        id,
        &LandEvent {
            base_ref: &base_ref,
            commit: &commit,
            branch,
            pushed,
        },
    )?;
    let (evidence, done, ci_override) = guards;
    if let Some(note) = ci_override {
        ledger.append(
            id,
            EventBody::Comment(CommentData {
                subtype: CommentSubtype::Decision,
                body: note.to_owned(),
            }),
        )?;
        tracing::warn!(ticket = %id, note, "base CI override recorded");
    }
    let exempt = done.record_exemption(ledger, id)?;
    tracing::info!(ticket = %id, exempt = exempt.is_some(), "land audited the changelog exemption before closing");
    let defaults = default_close_guards();
    let mut guards: Vec<&dyn CloseGuard> = defaults.iter().map(|g| &**g).collect();
    guards.push(evidence);
    guards.push(done);
    let applied = ledger.close(
        id,
        Some(opts.outcome),
        opts.reason
            .clone()
            .or_else(|| opts.no_evidence_reason.clone())
            .or_else(|| opts.no_changelog_reason.clone()),
        &guards,
    )?;
    if !applied.already {
        let recorded = evidence.record_bypass(ledger, id)?;
        tracing::info!(ticket = %id, bypass = recorded.is_some(), "land closed the ticket");
    }
    Ok(())
}

/// Push `base` to `origin`; a failure is a warning because the local land is done.
fn push_base(repo: &Repo, base: &str, warnings: &mut Vec<String>) -> bool {
    match repo.push("origin", base) {
        Ok(()) => {
            tracing::info!(base, "base pushed");
            true
        }
        Err(e) => {
            tracing::warn!(error = %e, "push failed after landing");
            warnings.push(format!(
                "landed locally but the push failed: {e}; run `git push origin {base}`"
            ));
            false
        }
    }
}

/// Release the lease after landing; a failure is a warning.
fn release(leases: &LeaseStore, id: TicketId, actor: &str, warnings: &mut Vec<String>) {
    match leases.release(id, Some(actor)) {
        Ok(_) => tracing::info!(ticket = %id, "lease released by land"),
        Err(e) => {
            tracing::warn!(error = %e, "lease release failed after landing");
            warnings.push(format!("the lease was not released: {e}"));
        }
    }
}

// frob:ticket 01M41RK1G648EJJNRK4G5RJY40
/// True when `cwd` is `dir` or lies inside it (compared on canonical paths, falling back to the raw ones).
fn is_inside(cwd: &Path, dir: &Path) -> bool {
    let canon = |p: &Path| gob_exec::canonical(p).unwrap_or_else(|_| p.to_path_buf());
    canon(cwd).starts_with(canon(dir))
}

/// Move this process out of the worktree about to be removed: Windows refuses to delete a directory that is some process's cwd, and `land` runs from inside it.
fn leave_worktree(wt_path: &Path, primary: &Path) {
    let Ok(cwd) = std::env::current_dir() else {
        return;
    };
    if !is_inside(&cwd, wt_path) {
        return;
    }
    match std::env::set_current_dir(primary) {
        Ok(()) => tracing::info!(to = %primary.display(), "left the worktree before removing it"),
        Err(e) => tracing::warn!(error = %e, "could not leave the worktree; removal may fail"),
    }
}

/// Suffix of a worktree directory renamed aside and waiting for its background deletion.
const REMOVING_SUFFIX: &str = ".removing";

/// Rename `wt_path` aside in one step and delete it (and any earlier leftovers) on a background thread.
///
/// Deleting a worktree with a large build directory took 4-9 s of the land
/// (frob:ticket 01M4D6NFCDSW5E4FD9X8J3BE8W); a rename is instant, and the caller prunes the
/// now-dangling registration. The process may exit before the deletion finishes: the next
/// land sweeps the `.removing` leftover. Returns false when the rename failed (the caller
/// then removes the worktree through git).
fn detach_worktree(wt_path: &Path) -> bool {
    let (Some(parent), Some(name)) = (wt_path.parent(), wt_path.file_name()) else {
        return false;
    };
    let mut aside_name = name.to_os_string();
    aside_name.push(REMOVING_SUFFIX);
    let aside = parent.join(aside_name);
    if let Err(e) = std::fs::rename(wt_path, &aside) {
        tracing::warn!(error = %e, "worktree not renamed aside; removing it through git");
        return false;
    }
    tracing::info!(aside = %aside.display(), "worktree renamed aside; deleting in the background");
    let parent = parent.to_path_buf();
    std::thread::spawn(move || sweep_removing(&parent));
    true
}

/// Delete every `*.removing` directory directly under `parent`; failures are logged.
fn sweep_removing(parent: &Path) {
    let Ok(entries) = std::fs::read_dir(parent) else {
        return;
    };
    for e in entries.flatten() {
        if !e.file_name().to_string_lossy().ends_with(REMOVING_SUFFIX) {
            continue;
        }
        match std::fs::remove_dir_all(e.path()) {
            Ok(()) => {
                tracing::info!(dir = %e.path().display(), "background worktree deletion done");
            }
            Err(err) => {
                tracing::warn!(dir = %e.path().display(), error = %err, "background worktree deletion failed");
            }
        }
    }
}

/// Remove the worktree and its (now merged) branch; failures are warnings because the land is done.
fn remove_worktree(
    repo: &Repo,
    primary: &Path,
    wt_path: &Path,
    branch: &str,
    base: &str,
    warnings: &mut Vec<String>,
) -> bool {
    leave_worktree(wt_path, primary);
    let path = wt_path.to_string_lossy();
    let merged = repo
        .rev_parse(branch)
        .is_ok_and(|b| repo.merge_base(&base_ref(base), branch).ok().flatten() == Some(b));
    let mut cleanup: Vec<(&str, Vec<&str>)> = if detach_worktree(wt_path) {
        vec![("worktree prune", vec!["worktree", "prune"])]
    } else {
        vec![(
            "worktree remove",
            vec!["worktree", "remove", "--force", &path],
        )]
    };
    if merged {
        cleanup.push(("branch delete", vec!["branch", "-D", branch]));
    } else {
        warnings.push(format!(
            "{branch} is not contained in {base}; the branch was kept"
        ));
    }
    let mut ok = true;
    for (label, args) in cleanup {
        match git(repo, primary, &args) {
            Ok(r) if r.ok() => tracing::info!(label, "land cleanup step done"),
            Ok(r) => {
                ok = false;
                warnings.push(format!("{label} failed: {}", r.text));
            }
            Err(e) => {
                ok = false;
                warnings.push(format!("{label} failed: {e}"));
            }
        }
    }
    ok
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M4GRW6NH23YPTSAQED5ZJPVH
    // frob:tests crates/frob-land/src/land.rs::touches_cone
    #[test]
    fn a_base_move_forces_a_recheck_only_when_it_touches_the_cone() {
        let ledger = frob_ledger::LedgerConfig::default();
        let change = |path: &str| gob_git::ChangedPath {
            path: path.to_owned(),
            kind: gob_git::ChangeKind::Modified,
        };
        let cone: BTreeSet<String> = ["src/a.rs".to_owned()].into_iter().collect();
        let ledger_path = format!("{}/T-1.toml", ledger.dir);
        let scope = ["lib/**".to_owned()];
        let touches = |paths: &[&str], cone: Option<&BTreeSet<String>>| {
            let changes: Vec<_> = paths.iter().map(|p| change(p)).collect();
            touches_cone(&changes, cone, &scope, &ledger)
        };
        assert!(!touches(&[&ledger_path], Some(&cone)));
        assert!(!touches(&["src/other.rs"], Some(&cone)));
        assert!(touches(&["src/a.rs"], Some(&cone)));
        assert!(
            touches(&["lib/new.rs"], Some(&cone)),
            "added under the scope globs"
        );
        assert!(touches(&["src/other.rs"], None));
        assert!(!touches(&[], None));
    }

    // frob:ticket 01M4D6NFCDSW5E4FD9X8J3BE8W
    // frob:tests crates/frob-land/src/land.rs::detach_worktree
    #[test]
    fn a_detached_worktree_vanishes_at_once_and_its_leftover_is_swept() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let wt = tmp.path().join("wt");
        std::fs::create_dir_all(wt.join("src")).expect("mkdir");
        let stale = tmp.path().join(format!("old{REMOVING_SUFFIX}"));
        std::fs::create_dir_all(&stale).expect("stale");
        assert!(detach_worktree(&wt));
        assert!(!wt.exists(), "the worktree path is free immediately");
        sweep_removing(tmp.path());
        assert!(!stale.exists());
        assert!(!tmp.path().join(format!("wt{REMOVING_SUFFIX}")).exists());
    }

    // frob:ticket 01M41RK1G648EJJNRK4G5RJY40
    // frob:tests crates/frob-land/src/land.rs::is_inside
    #[test]
    fn is_inside_is_true_for_the_dir_and_its_descendants_only() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let wt = tmp.path().join("wt");
        let sub = wt.join("src");
        std::fs::create_dir_all(&sub).expect("mkdir");
        let sibling = tmp.path().join("wt-other");
        std::fs::create_dir_all(&sibling).expect("mkdir");
        assert!(is_inside(&wt, &wt));
        assert!(is_inside(&sub, &wt));
        assert!(
            !is_inside(&sibling, &wt),
            "a name prefix is not containment"
        );
        assert!(!is_inside(tmp.path(), &wt));
    }
}
