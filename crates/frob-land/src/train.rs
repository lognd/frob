//! The merge train: land several ready tickets as one speculative batch (frob:ticket 01M4MH62H1AE14Z472QDSD1QBK).
//!
//! Tickets with pairwise disjoint scopes cannot conflict, so their branches are
//! merged into a scratch checkout of the base and that combined tree is verified
//! once instead of once per ticket (the precedent is GitHub's merge queue, Bors
//! and Zuul's speculative execution). When the batch verifies, every ticket lands
//! in order with the per-ticket check skipped. When it fails, the largest passing
//! prefix is found by bisection, that prefix lands, and the first ticket after it
//! (the culprit) and the rest are deferred, still leased and untouched.

use std::path::{Path, PathBuf};
use std::sync::Arc;

use frob_check::CheckOptions;
use frob_ledger::LedgerConfig;
use gob_git::Repo;
use gob_time::Clock;
use schemars::JsonSchema;
use serde::Serialize;

use crate::error::{LandError, needs_action};
use crate::git::git;
use crate::land::{base_ref, held_lease, land, primary_root, resolve, work_dir};
use crate::plan::{LandOptions, LandOutcome};
use crate::ratchet;

/// Verifies one combined tree; a seam so tests can inject a failing member.
pub trait TrainVerifier {
    /// Check the batch tree at `tree`, which merges the branches of `members` (handles) into the base.
    ///
    /// # Errors
    ///
    /// The reason the combined tree is red.
    fn verify(&self, tree: &Path, members: &[String]) -> Result<(), String>;
}

/// Options of [`land_train`].
#[derive(Clone)]
pub struct TrainOptions {
    /// The tickets to land, in landing order (`~handle`, ULID or alias).
    pub handles: Vec<String>,
    /// Options each member lands with; its `handle` and `prechecked` are overwritten.
    pub land: LandOptions,
    /// The batch verifier; the ratcheted `frob check` of the combined tree when absent.
    pub verifier: Option<Arc<dyn TrainVerifier>>,
}

/// What a train did.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TrainOutcome {
    /// The members that landed, in order.
    pub landed: Vec<LandOutcome>,
    /// Handles left leased and unlanded: the culprit and everything after it.
    pub deferred: Vec<String>,
    /// The first ticket whose addition made the batch red, when the batch failed.
    pub culprit: Option<String>,
    /// Why the culprit's prefix was red.
    pub failure: Option<String>,
    /// How many times a combined tree was verified.
    pub verifications: u32,
    /// Why landing stopped early after a verified prefix (a member's own land refused).
    pub stopped: Option<String>,
}

/// One train member: its handle, scope globs, branch and the worktree holding it.
struct Member {
    handle: String,
    scope: Vec<String>,
    branch: String,
}

/// Land `opts.handles` as one speculative batch from the repository containing `root`.
///
/// # Errors
///
/// `E-TRAIN-EMPTY`, `E-TRAIN-OVERLAP` (two scopes may conflict), the lease and
/// worktree refusals of [`land`] for a member, and git or check failures.
pub fn land_train(
    root: &Path,
    opts: &TrainOptions,
    clock: &Arc<dyn Clock>,
) -> Result<TrainOutcome, LandError> {
    if opts.handles.is_empty() {
        return Err(needs_action(
            "E-TRAIN-EMPTY",
            "no tickets were given",
            "frob land --train <ticket>...",
        ));
    }
    let repo = Repo::discover(root).map_err(|e| LandError::Config(e.to_string()))?;
    let cwd_root = work_dir(&repo)?;
    let primary = primary_root(&repo)?;
    let here = frob_evidence::Workspace::open(&cwd_root, clock.clone())?;
    let (leases, _) = frob_lease::open_store_from_file(&cwd_root, clock.clone())?;
    let base = frob_worktree::work::base_branch(&here.ledger);
    let members = resolve_members(&repo, &here.ledger, &leases, &cwd_root, &opts.handles)?;
    ensure_disjoint(&members)?;
    tracing::info!(count = members.len(), base = %base, "merge train started");

    let verifier: Arc<dyn TrainVerifier> = match &opts.verifier {
        Some(v) => v.clone(),
        None => Arc::new(CheckVerifier {
            root: cwd_root.clone(),
            primary: primary.clone(),
            ledger: here.ledger.config().clone(),
            base_oid: repo.rev_parse(&base_ref(&base))?.to_string(),
        }),
    };
    let mut out = TrainOutcome {
        landed: Vec::new(),
        deferred: Vec::new(),
        culprit: None,
        failure: None,
        verifications: 0,
        stopped: None,
    };
    let mut verify_prefix = |n: usize| -> Result<Result<(), String>, LandError> {
        out.verifications += 1;
        verify_batch(&repo, &primary, &base, &members[..n], verifier.as_ref())
    };
    let count = members.len();
    let good = match verify_prefix(count)? {
        Ok(()) => count,
        Err(first) => {
            tracing::warn!(reason = %first, "the full batch is red; bisecting for the passing prefix");
            let (mut lo, mut hi, mut why) = (0_usize, count, first);
            while hi - lo > 1 {
                let mid = lo + (hi - lo) / 2;
                match verify_prefix(mid)? {
                    Ok(()) => lo = mid,
                    Err(e) => {
                        hi = mid;
                        why = e;
                    }
                }
            }
            out.culprit = Some(members[lo].handle.clone());
            out.failure = Some(why);
            lo
        }
    };
    out.deferred = members[good..].iter().map(|m| m.handle.clone()).collect();
    for m in &members[..good] {
        let mut member_opts = opts.land.clone();
        member_opts.handle = Some(m.handle.clone());
        member_opts.prechecked = true;
        match land(root, &member_opts, clock) {
            Ok(done) => out.landed.push(done),
            Err(e) => {
                tracing::warn!(ticket = %m.handle, error = %e, "train member refused its land");
                out.stopped = Some(format!("{}: {e}", m.handle));
                let rest = members
                    .iter()
                    .position(|x| x.handle == m.handle)
                    .unwrap_or(0);
                out.deferred = members[rest..].iter().map(|x| x.handle.clone()).collect();
                break;
            }
        }
    }
    tracing::info!(
        landed = out.landed.len(),
        deferred = out.deferred.len(),
        verifications = out.verifications,
        "merge train finished"
    );
    Ok(out)
}

/// Resolve each handle to its scope and ticket branch, requiring the caller's live lease.
fn resolve_members(
    repo: &Repo,
    ledger: &frob_ledger::Ledger,
    leases: &frob_lease::LeaseStore,
    cwd_root: &Path,
    handles: &[String],
) -> Result<Vec<Member>, LandError> {
    let mut members = Vec::new();
    for h in handles {
        let id = resolve(ledger, leases, cwd_root, Some(h))?;
        let view = ledger.show(id)?;
        let handle = view.summary.handle.clone();
        let lease = held_lease(repo, leases, ledger, &view, id, &handle, cwd_root)?;
        let wt =
            Repo::discover(&lease.holder.worktree).map_err(|e| LandError::Config(e.to_string()))?;
        let branch = wt.current_branch()?.ok_or_else(|| {
            needs_action(
                "E-LAND-WRONG-WORKTREE",
                format!("{handle}'s worktree has a detached HEAD"),
                format!("frob work {handle}"),
            )
        })?;
        members.push(Member {
            handle,
            scope: view.ticket.front.scope.clone(),
            branch,
        });
    }
    Ok(members)
}

/// Refuse a batch whose scopes might overlap: speculation is only sound for disjoint tickets.
fn ensure_disjoint(members: &[Member]) -> Result<(), LandError> {
    for (i, a) in members.iter().enumerate() {
        for b in &members[i + 1..] {
            for (ga, gb) in a
                .scope
                .iter()
                .flat_map(|ga| b.scope.iter().map(move |gb| (ga, gb)))
            {
                if frob_lease::overlap::globs_overlap(ga, gb)? {
                    return Err(needs_action(
                        "E-TRAIN-OVERLAP",
                        format!(
                            "{} (`{ga}`) and {} (`{gb}`) may touch the same files",
                            a.handle, b.handle
                        ),
                        "land them one at a time, or leave one out of the train",
                    ));
                }
            }
        }
    }
    Ok(())
}

/// Merge `members` into a scratch checkout of the base and verify it; the inner error is a red verdict.
fn verify_batch(
    repo: &Repo,
    primary: &Path,
    base: &str,
    members: &[Member],
    verifier: &dyn TrainVerifier,
) -> Result<Result<(), String>, LandError> {
    let dir = scratch_dir(repo);
    let text = dir.to_string_lossy().into_owned();
    let added = git(
        repo,
        primary,
        &["worktree", "add", "--detach", &text, &base_ref(base)],
    )?;
    if !added.ok() {
        return Err(LandError::Config(format!(
            "could not create the train checkout: {}",
            added.text
        )));
    }
    let verdict = (|| {
        for m in members {
            let merged = git(
                repo,
                &dir,
                &[
                    "-c",
                    "user.name=frob",
                    "-c",
                    "user.email=frob@localhost",
                    "merge",
                    "--no-edit",
                    &m.branch,
                ],
            )?;
            if !merged.ok() {
                let _ = git(repo, &dir, &["merge", "--abort"]);
                return Ok(Err(format!(
                    "merging {} into the batch failed: {}",
                    m.handle, merged.text
                )));
            }
        }
        let handles: Vec<String> = members.iter().map(|m| m.handle.clone()).collect();
        Ok(verifier.verify(&dir, &handles))
    })();
    let removed = git(repo, primary, &["worktree", "remove", "--force", &text])?;
    if !removed.ok() {
        tracing::warn!(dir = %dir.display(), "train checkout not removed: {}", removed.text);
    }
    tracing::info!(members = members.len(), green = ?verdict.as_ref().map(Result::is_ok), "batch verified");
    verdict
}

/// A fresh scratch path under the git common dir.
fn scratch_dir(repo: &Repo) -> PathBuf {
    repo.common_dir().join("frob").join(format!(
        "train-{}-{}",
        std::process::id(),
        gob_time::SystemClock::entropy_nanos() % 1_000_000
    ))
}

/// The default verifier: the unscoped check of the combined tree, ratcheted against the base tip.
struct CheckVerifier {
    root: PathBuf,
    primary: PathBuf,
    ledger: LedgerConfig,
    base_oid: String,
}

impl TrainVerifier for CheckVerifier {
    fn verify(&self, tree: &Path, _members: &[String]) -> Result<(), String> {
        let repo = Repo::discover(&self.root).map_err(|e| e.to_string())?;
        ratchet::share_build_dir(repo.common_dir(), tree);
        let base = ratchet::base_findings(&repo, &self.primary, &self.base_oid, &self.ledger)
            .map_err(|e| e.to_string())?;
        let report = frob_check::run(
            tree,
            &CheckOptions {
                ledger: Some(self.ledger.clone()),
                skip_telemetry: true,
                ..CheckOptions::default()
            },
        )
        .map_err(|e| e.to_string())?;
        let new = ratchet::new_blocking(&report, &base);
        if new.is_empty() {
            return Ok(());
        }
        Err(new
            .iter()
            .take(5)
            .map(|n| {
                format!(
                    "{} {}: {}",
                    n.rule,
                    n.path.as_deref().unwrap_or("-"),
                    n.message
                )
            })
            .collect::<Vec<_>>()
            .join("; "))
    }
}
