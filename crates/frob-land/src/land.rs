//! The land transaction: preconditions, then the locked publish (tickets.md section 10, D25).
//!
//! Order: resolve and vet the lease, check the worktree is the holder's and
//! clean, merge the base into the ticket branch (refusing on conflicts), run
//! the ticket-scoped check and the close guards, then under the land lock
//! fast-forward the base branch, write the `land` event, close the ticket,
//! release the lease and remove the worktree. A dry run stops after the
//! preconditions and prints the plan.
//!
//! The base branch is advanced by spawning git through `gob-exec`:
//! `git merge --ff-only <oid>` in the checkout that has the base checked out
//! (git then updates that index and worktree itself), or
//! `git update-ref <ref> <new> <old>` (compare-and-swap) when no checkout
//! has it. `gob-git` has no ref-update or worktree-removal API yet.

use std::fmt::Write as _;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use frob_check::CheckOptions;
use frob_evidence::{DoneGuard, EvidenceGuard, Workspace};
use frob_lease::{Lease, LeaseStore};
use frob_ledger::guards::{CloseContext, CloseGuard, default_close_guards};
use frob_ledger::model::Category;
use frob_ledger::ops::TicketView;
use frob_ledger::{Ledger, RefMode, TicketId};
use gob_diagnostics::{ExitCode, Refusal, RefusalClass};
use gob_git::{MergeOutcome, Oid, Repo, StatusOptions, TreeRef};

use crate::error::{LandError, needs_action};
use crate::events::{LandEvent, append_land};
use crate::git::git;
use crate::lock::LandLock;
use crate::plan::{LandOptions, LandOutcome, PlanInputs, RetryPolicy, digest, steps};

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
pub fn land(root: &Path, opts: &LandOptions) -> Result<LandOutcome, LandError> {
    let repo = Repo::discover(root).map_err(|e| LandError::Config(e.to_string()))?;
    let cwd_root = work_dir(&repo)?;
    let here = Workspace::open(&cwd_root)?;
    let (leases, _) = frob_lease::open_store_from_file(&cwd_root)?;
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
    site: Workspace,
    evidence: EvidenceGuard,
    done: DoneGuard,
    out: LandOutcome,
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
    let id = view.ticket.front.id;
    let handle = view.summary.handle.clone();
    let lease = held_lease(leases, &here.ledger, view, id, &handle)?;
    let wt_path = lease.holder.worktree.clone();
    let primary = primary_root(&repo)?;
    check_worktree(&repo, cwd_root, &wt_path, &handle)?;
    let wt = Repo::discover(&wt_path).map_err(|e| LandError::Config(e.to_string()))?;
    let branch = ticket_branch(&wt, base, &wt_path, &handle)?;
    ensure_clean(&wt, &wt_path)?;

    let base_oid = wt.rev_parse(base).map_err(|_| {
        needs_action(
            "E-LAND-NO-BASE",
            format!("base branch `{base}` does not exist"),
            "set [tickets] ref to an existing branch in frob.toml",
        )
    })?;
    let mut base_merge = None;
    let mut base_merged = wt.merge_base(base, &branch)? == Some(base_oid);
    if !base_merged && !opts.dry_run {
        base_merge = Some(merge_base_in(&wt, &wt_path, base, &handle)?);
        base_merged = true;
    } else if base_merged {
        base_merge = Some("up-to-date".to_owned());
    }
    let mut warnings = Vec::new();
    if base_merged {
        verify_check(&wt_path, &here.ledger, &handle, base, opts)?;
    } else {
        // A dry run leaves the base unmerged, so the ticket-scoped diff would
        // include the base's own changes; the real land merges first.
        warnings.push(format!(
            "check skipped: {base} is not merged into {branch} yet and a dry run does not merge it"
        ));
    }

    let site = if here.ledger.config().mode == RefMode::Branch {
        Workspace::open(&wt_path)?
    } else if primary == cwd_root {
        here
    } else {
        Workspace::open(&primary)?
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
    let mut done_view = view.ticket.clone();
    done_view.front.outcome = Some(opts.outcome);
    warnings.extend(done.warnings(&done_view));
    let out = LandOutcome {
        branch: Some(branch.clone()),
        worktree: Some(wt_path.clone()),
        base_merge,
        warnings,
        ..empty_outcome(id, &handle, base, opts)
    };
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
        let base_oid = self.wt.rev_parse(&self.base)?.to_string();
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
        let retrying = opts.wait_secs > 0;
        let budget = opts
            .retry
            .budget
            .unwrap_or_else(|| Duration::from_secs(opts.wait_secs));
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
                    (evidence, done),
                    opts,
                    base,
                    branch,
                    false,
                )
            });
            match advanced {
                Err(LandError::Refused(r)) if retrying && r.code == CODE_STALE => {
                    ctx.recover_stale(&site.ledger, opts, attempt, started, budget)?;
                }
                other => break other?,
            }
        };
        self.out.attempts = attempt;
        self.out.commit = Some(oid.to_string());
        if opts.push {
            self.out.pushed = push_base(&self.repo, &self.base, &mut self.out.warnings);
        }
        if !on_branch {
            ledger_step(
                &self.site.ledger,
                self.id,
                (&self.evidence, &self.done),
                opts,
                &self.base,
                &self.branch,
                self.out.pushed,
            )?;
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
        tracing::info!(ticket = %self.id, commit = %oid, pushed = self.out.pushed, "land complete");
        Ok(self.out)
    }
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
    std::fs::canonicalize(path).unwrap_or_else(|_| path.to_path_buf())
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
    leases: &LeaseStore,
    ledger: &Ledger,
    view: &TicketView,
    id: TicketId,
    handle: &str,
) -> Result<Lease, LandError> {
    let not_leased =
        |why: String| needs_action("E-LAND-NOT-LEASED", why, format!("frob work {handle}"));
    if view.summary.category != Category::InProgress {
        return Err(not_leased(format!(
            "{handle} is {}, not in progress",
            view.summary.category
        )));
    }
    let Some(lease) = leases.live_lease(id)? else {
        return Err(not_leased(format!("{handle} has no live lease")));
    };
    let actor = ledger.actor()?;
    if lease.holder.actor != actor {
        return Err(not_leased(format!(
            "{handle} is leased by {}, not {actor}",
            lease.holder
        )));
    }
    Ok(lease)
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

/// Merge `base` into the ticket branch inside its worktree; conflicts are listed and the merge aborted.
fn merge_base_in(wt: &Repo, wt_path: &Path, base: &str, handle: &str) -> Result<String, LandError> {
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

/// Run the ticket-scoped check in the worktree; any finding at the configured `fail_on` refuses.
fn verify_check(
    wt_path: &Path,
    ledger: &Ledger,
    handle: &str,
    base: &str,
    opts: &LandOptions,
) -> Result<(), LandError> {
    let report = frob_check::run(
        wt_path,
        &CheckOptions {
            ticket: Some(handle.to_owned()),
            base: Some(base.to_owned()),
            ledger: Some(ledger.config().clone()),
            skip_telemetry: true,
            changelog_exempt: opts.no_changelog_reason.is_some(),
            ..CheckOptions::default()
        },
    )?;
    if report.exit_code() == ExitCode::Ok {
        tracing::info!(findings = report.findings.len(), "land check green");
        return Ok(());
    }
    // Reuse the gate's own predicate on one finding at a time so the list matches the verdict.
    let mut blocking: Vec<_> = report
        .findings
        .iter()
        .filter(|f| {
            gob_diagnostics::fail_on(
                std::slice::from_ref(*f),
                report.fail_on.threshold(),
                report.fail_on_unresolved,
            ) != ExitCode::Ok
        })
        .collect();
    blocking.sort_by_key(|f| std::cmp::Reverse(f.severity));
    let non_blocking = report.findings.len() - blocking.len();
    tracing::warn!(blocking = blocking.len(), non_blocking, "land check red");
    let listed: Vec<String> = blocking
        .iter()
        .take(LIST_CAP)
        .map(|f| {
            let at = f
                .span
                .as_ref()
                .and_then(|s| report.files.path(s.file))
                .unwrap_or("-");
            format!("{} {at}: {}", f.rule, f.message)
        })
        .collect();
    let hidden = blocking.len().saturating_sub(LIST_CAP);
    let mut tail = String::new();
    if hidden > 0 {
        let _ = write!(tail, "; and {hidden} more blocking finding(s)");
    }
    if non_blocking > 0 {
        let _ = write!(tail, "; and {non_blocking} non-blocking findings");
    }
    Err(LandError::Refused(
        Refusal::new(
            "E-LAND-CHECK-RED",
            RefusalClass::GuardNeedsAction,
            format!(
                "frob check --ticket {handle} has {} blocking finding(s) at or above fail_on ({:?}): {}{tail}",
                blocking.len(),
                report.fail_on,
                listed.join("; ")
            ),
        )
        .with_remedy(format!("frob check --ticket {handle}")),
    ))
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
    /// Ledger-only moves cannot change the check verdict, so the check is
    /// skipped unless a path outside the ledger directory differs between the
    /// base the branch contained and the new base. Nothing is written before
    /// the compare-and-swap succeeds, so a crash here resumes with `frob land`.
    fn recover_stale(
        &self,
        ledger: &Ledger,
        opts: &LandOptions,
        attempt: u32,
        started: Instant,
        budget: Duration,
    ) -> Result<(), LandError> {
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
        let had = self.wt.merge_base(self.base, self.branch)?;
        let wt_path = self
            .wt
            .work_dir()
            .map(Path::to_path_buf)
            .ok_or_else(|| LandError::Config("not inside a git work tree".to_owned()))?;
        let how = merge_base_in(self.wt, &wt_path, self.base, self.handle)?;
        let now = self.wt.rev_parse(self.base)?;
        let code_changed = match had {
            Some(old) if old != now => {
                let prefix = format!("{}/", ledger.config().dir.trim_end_matches('/'));
                self.wt
                    .diff_names(&TreeRef::Oid(old), &TreeRef::Oid(now))?
                    .iter()
                    .any(|c| !c.path.starts_with(&prefix))
            }
            Some(_) => false,
            None => true,
        };
        tracing::info!(attempt, merge = %how, code_changed, "stale base re-merged");
        if code_changed {
            verify_check(&wt_path, ledger, self.handle, self.base, opts)?;
        }
        Ok(())
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
        let base_oid = self.wt.rev_parse(self.base)?;
        if self.wt.merge_base(self.base, self.branch)? != Some(base_oid) {
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
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |d| d.as_nanos());
    let mut h = blake3::Hasher::new();
    h.update(&nanos.to_le_bytes());
    h.update(&attempt.to_le_bytes());
    h.update(salt.as_bytes());
    let bytes = h.finalize();
    let draw = u64::from_le_bytes(bytes.as_bytes()[..8].try_into().expect("8 bytes"));
    let ceil_nanos = u64::try_from(ceiling.as_nanos()).unwrap_or(u64::MAX).max(1);
    Duration::from_nanos(draw % ceil_nanos)
}

/// Record the `land` event, close the ticket through the guards and audit an evidence bypass.
fn ledger_step(
    ledger: &Ledger,
    id: TicketId,
    guards: (&EvidenceGuard, &DoneGuard),
    opts: &LandOptions,
    base: &str,
    branch: &str,
    pushed: bool,
) -> Result<(), LandError> {
    let commit = ledger
        .repo()
        .rev_parse(&format!("refs/heads/{branch}"))
        .or_else(|_| ledger.repo().rev_parse(base))?
        .to_string();
    let base_ref = format!("refs/heads/{base}");
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
    let (evidence, done) = guards;
    let exempt = done.record_exemption(ledger, id)?;
    tracing::info!(ticket = %id, exempt = exempt.is_some(), "land audited the changelog exemption before closing");
    let defaults = default_close_guards();
    let mut guards: Vec<&dyn CloseGuard> = defaults.iter().map(|g| &**g).collect();
    guards.push(evidence);
    guards.push(done);
    let applied = ledger.close(
        id,
        Some(opts.outcome),
        opts.no_evidence_reason
            .clone()
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

/// Remove the worktree and its (now merged) branch; failures are warnings because the land is done.
fn remove_worktree(
    repo: &Repo,
    primary: &Path,
    wt_path: &Path,
    branch: &str,
    base: &str,
    warnings: &mut Vec<String>,
) -> bool {
    let path = wt_path.to_string_lossy();
    let merged = repo
        .rev_parse(branch)
        .is_ok_and(|b| repo.merge_base(base, branch).ok().flatten() == Some(b));
    let mut cleanup: Vec<(&str, Vec<&str>)> = vec![(
        "worktree remove",
        vec!["worktree", "remove", "--force", &path],
    )];
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
