//! Collecting ticket worktrees: remove only what is provably finished and fully saved.
//!
//! A linked worktree is a candidate only when it sits (by path components) under the
//! worktree parent frob created, is checked out on `ticket/<handle>`, holds no live
//! lease, is not the current directory, and its ticket is known to the ledger. It is
//! then kept, with the reason reported, when it has uncommitted changes; and, when
//! the ticket is still open, also when its branch holds commits that are neither in
//! the base nor on any remote. What remains is removed with plain `git worktree remove`
//! (no `--force`, so git itself refuses anything it considers unclean). The branch is
//! deleted only for a closed ticket whose branch is merged into the base.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::path::{Path, PathBuf};

use gob_git::{Repo, StatusOptions};

use super::git::git;
use super::jail::Jail;
use super::pass::{TicketOracle, TicketState};
use super::scan::scan;

/// Everything the assessment needs to know about the repository around the worktrees.
pub struct WorktreeEnv<'a> {
    /// The repository (any checkout of it).
    pub repo: &'a Repo,
    /// The primary checkout; never a candidate.
    pub primary: &'a Path,
    /// The directory frob creates ticket worktrees in.
    pub parent: &'a Path,
    /// Short name of the base branch.
    pub base: &'a str,
    /// Worktree paths named by a live lease.
    pub live: &'a [PathBuf],
    /// Ticket states.
    pub tickets: &'a dyn TicketOracle,
    /// Path admission for removals.
    pub jail: &'a Jail,
    /// This process's working directory, when known.
    pub cwd: Option<PathBuf>,
}

/// What to do with one worktree.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Decision {
    /// Remove the worktree; also delete the branch when `delete_branch`.
    Remove {
        /// The ticket branch checked out there.
        branch: String,
        /// True for a closed ticket whose branch is merged into the base.
        delete_branch: bool,
    },
    /// Leave it, for this reason.
    Keep(String),
}

/// One worktree and the decision about it.
#[derive(Debug, Clone)]
pub struct Candidate {
    /// The worktree directory.
    pub path: PathBuf,
    /// The decision.
    pub decision: Decision,
}

/// True when `path` is `of` or lies inside it, comparing canonical forms by components.
fn inside(path: &Path, of: &Path) -> bool {
    let canon = |p: &Path| gob_exec::canonical(p).unwrap_or_else(|_| p.to_path_buf());
    canon(path).starts_with(canon(of))
}

/// Assess every linked worktree of the repository.
pub fn assess(env: &WorktreeEnv<'_>) -> Vec<Candidate> {
    let infos = match env.repo.list_worktrees() {
        Ok(i) => i,
        Err(e) => {
            tracing::warn!(error = %e, "gc could not list worktrees");
            return Vec::new();
        }
    };
    let primary = gob_exec::canonical(env.primary).unwrap_or_else(|_| env.primary.to_path_buf());
    let parent = gob_exec::canonical(env.parent).ok();
    let mut out = Vec::new();
    for info in infos {
        if gob_exec::canonical(&info.path).unwrap_or_else(|_| info.path.clone()) == primary {
            continue;
        }
        let decision = decide(env, parent.as_deref(), &info.path, info.branch.as_deref());
        tracing::info!(path = %info.path.display(), ?decision, "gc worktree assessed");
        out.push(Candidate {
            path: info.path,
            decision,
        });
    }
    out
}

fn keep(why: impl Into<String>) -> Decision {
    Decision::Keep(why.into())
}

fn decide(
    env: &WorktreeEnv<'_>,
    parent: Option<&Path>,
    path: &Path,
    branch: Option<&str>,
) -> Decision {
    let canon = match env.jail.admit(path) {
        Ok(c) => c,
        Err(e) => return keep(e.to_string()),
    };
    if !parent.is_some_and(|p| canon.starts_with(p)) {
        return keep("not under the worktree directory frob created");
    }
    let Some(branch) = branch else {
        return keep("detached HEAD, not a ticket worktree");
    };
    let Some(name) = branch.strip_prefix("ticket/") else {
        return keep("not on a ticket branch");
    };
    if env.live.iter().any(|l| inside(l, &canon)) {
        return keep("a live lease holds it");
    }
    if env.cwd.as_deref().is_some_and(|c| inside(c, &canon)) {
        return keep("the current directory is inside it");
    }
    let state = env.tickets.state(&format!("~{name}"));
    if state == TicketState::Unknown {
        return keep("its ticket is not in the ledger");
    }
    match dirty_paths(&canon) {
        Ok(0) => {}
        Ok(n) => return keep(format!("{n} uncommitted change(s)")),
        Err(e) => return keep(format!("status unavailable: {e}")),
    }
    let merged = is_merged(env, branch);
    match state {
        TicketState::Closed => Decision::Remove {
            branch: branch.to_owned(),
            delete_branch: merged,
        },
        TicketState::Open => {
            if merged || is_pushed(env, branch) {
                Decision::Remove {
                    branch: branch.to_owned(),
                    delete_branch: false,
                }
            } else {
                keep("unpushed commits on a ticket that is still open")
            }
        }
        TicketState::Unknown => keep("its ticket is not in the ledger"),
    }
}

/// Number of changed or untracked paths in the checkout at `path`, ignoring frob's own `.frob/`.
fn dirty_paths(path: &Path) -> Result<usize, String> {
    let repo = Repo::discover(path).map_err(|e| e.to_string())?;
    let entries = repo
        .status(&StatusOptions::default())
        .map_err(|e| e.to_string())?;
    Ok(entries
        .iter()
        .filter(|e| !(e.path == ".frob" || e.path.starts_with(".frob/")))
        .count())
}

/// True when the branch tip is contained in the base.
fn is_merged(env: &WorktreeEnv<'_>, branch: &str) -> bool {
    let tip = env.repo.rev_parse(&format!("refs/heads/{branch}"));
    match (
        tip,
        env.repo
            .merge_base(env.base, &format!("refs/heads/{branch}")),
    ) {
        (Ok(t), Ok(Some(b))) => t == b,
        _ => false,
    }
}

/// True when some remote-tracking branch contains the branch tip.
fn is_pushed(env: &WorktreeEnv<'_>, branch: &str) -> bool {
    let Ok(tip) = env.repo.rev_parse(&format!("refs/heads/{branch}")) else {
        return false;
    };
    let tip = tip.to_string();
    match git(env.repo, env.primary, &["branch", "-r", "--contains", &tip]) {
        Ok((0, text)) => text.lines().any(|l| !l.trim().is_empty()),
        Ok(_) | Err(_) => false,
    }
}

/// Remove the worktree of a [`Decision::Remove`] candidate; returns the bytes it held.
///
/// # Errors
///
/// A message when the path is not admitted or git refuses to remove the worktree
/// (it is then left exactly as it was).
pub fn remove(env: &WorktreeEnv<'_>, cand: &Candidate) -> Result<u64, String> {
    let Decision::Remove {
        branch,
        delete_branch,
    } = &cand.decision
    else {
        return Err("not a removal".to_owned());
    };
    let canon = env.jail.admit(&cand.path).map_err(|e| e.to_string())?;
    let bytes = scan(&canon).bytes;
    let text = canon.to_string_lossy().into_owned();
    let (code, out) = git(env.repo, env.primary, &["worktree", "remove", &text])?;
    if code != 0 {
        return Err(format!(
            "git refused to remove {}: {}",
            canon.display(),
            out.trim()
        ));
    }
    tracing::info!(path = %canon.display(), bytes, "gc removed worktree");
    if *delete_branch {
        match git(env.repo, env.primary, &["branch", "-D", branch]) {
            Ok((0, _)) => tracing::info!(branch, "gc deleted merged ticket branch"),
            Ok((_, o)) => tracing::warn!(branch, output = %o.trim(), "gc kept the branch"),
            Err(e) => tracing::warn!(branch, error = %e, "gc kept the branch"),
        }
    }
    Ok(bytes)
}

/// Prune git's records of worktrees whose directories are gone.
pub fn prune(env: &WorktreeEnv<'_>) {
    if let Err(e) = git(env.repo, env.primary, &["worktree", "prune"]) {
        tracing::warn!(error = %e, "gc worktree prune failed");
    }
}
