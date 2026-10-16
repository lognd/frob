//! Candidate builder of the land train (frob:ticket 01M4Z1MYPEJ6HDVBJVPDVHR8MA).
//!
//! Merges ordered ticket branches into a temp ref `refs/frob/train/<id>` off a
//! base commit. A branch that conflicts is skipped (the train evicts it with git's
//! reason and the rest proceed) and its merge aborted; tickets whose lease scopes overlap are split into separate
//! trains. The temp ref is removed when the [`Candidate`] drops, and is never
//! created when the build fails.

use std::path::{Path, PathBuf};

use gob_git::Repo;

use crate::error::LandError;
use crate::git::git;
use crate::lockfile;

/// Namespace of the temp refs a train candidate lives on.
const TRAIN_REF_PREFIX: &str = "refs/frob/train/";
/// Directory (under `<common>/frob/`) of the persistent train checkout; not the `land-base-` prefix the gc sweeps.
const TRAIN_CHECKOUT_DIR: &str = "land-train-checkout";

/// One ticket offered to a candidate: its handle, ticket branch and lease scope globs.
#[derive(Debug, Clone)]
pub struct CandidateMember {
    /// Ticket handle, for logs and reports.
    pub handle: String,
    /// The ticket branch to merge.
    pub branch: String,
    /// The lease scope globs of the ticket.
    pub scope: Vec<String>,
    /// The branch head oid frozen at enqueue; the branch must still equal it to merge.
    pub oid: String,
}

/// A member left out of a candidate and why; it stays queued.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Skipped {
    /// Ticket handle.
    pub handle: String,
    /// Why the merge was skipped (git's output).
    pub reason: String,
}

/// A built candidate: the combined commit, held alive by a temp ref removed on drop.
#[derive(Debug)]
pub struct Candidate {
    /// The candidate commit (the base oid when nothing merged).
    pub oid: String,
    /// Handles merged, in order.
    pub merged: Vec<String>,
    /// Members skipped with reasons.
    pub skipped: Vec<Skipped>,
    ref_name: String,
    primary: PathBuf,
    checkout: PathBuf,
    _guard: std::fs::File,
}

impl Candidate {
    /// The persistent train checkout, left at the candidate commit and locked until `self` drops.
    pub fn checkout(&self) -> &Path {
        &self.checkout
    }

    /// The temp ref holding the candidate commit.
    pub fn ref_name(&self) -> &str {
        &self.ref_name
    }
}

impl Drop for Candidate {
    fn drop(&mut self) {
        delete_ref(&self.primary, &self.ref_name);
    }
}

/// Delete `ref_name`, logging (not failing) when it cannot be removed.
fn delete_ref(primary: &Path, ref_name: &str) {
    let removed = Repo::discover(primary)
        .map_err(|e| e.to_string())
        .and_then(|repo| {
            git(&repo, primary, &["update-ref", "-d", ref_name]).map_err(|e| e.to_string())
        });
    match removed {
        Ok(run) if run.ok() => tracing::info!(ref_name, "train temp ref removed"),
        Ok(run) => tracing::warn!(ref_name, "train temp ref not removed: {}", run.text),
        Err(e) => tracing::warn!(ref_name, "train temp ref not removed: {e}"),
    }
}

/// Split `members` into trains so no train holds two members with overlapping scopes; order is kept.
///
/// # Errors
///
/// A scope glob does not parse.
pub fn partition_trains(
    members: Vec<CandidateMember>,
) -> Result<Vec<Vec<CandidateMember>>, LandError> {
    let mut trains: Vec<Vec<CandidateMember>> = Vec::new();
    'next: for m in members {
        for train in &mut trains {
            if !train.iter().try_fold(false, |acc, t| {
                scopes_overlap(&t.scope, &m.scope).map(|o| acc || o)
            })? {
                train.push(m);
                continue 'next;
            }
        }
        tracing::info!(handle = %m.handle, trains = trains.len() + 1, "scope overlap: member placed in a new train");
        trains.push(vec![m]);
    }
    Ok(trains)
}

/// True when any glob of `a` may overlap any glob of `b` (the one scope-overlap test of the train).
pub(crate) fn scopes_overlap(a: &[String], b: &[String]) -> Result<bool, LandError> {
    for ga in a {
        for gb in b {
            if frob_lease::overlap::globs_overlap(ga, gb)? {
                return Ok(true);
            }
        }
    }
    Ok(false)
}

/// Build the candidate `id` off `base_oid` by merging `members` sequentially, skipping conflicting ones.
///
/// The merges run in the persistent train checkout (`<common>/frob/land-train-checkout`), locked
/// until the returned [`Candidate`] drops so the caller can check the result there with warm
/// build state. Each member is merged by its frozen oid; a member whose branch moved is skipped.
/// A conflict confined to shared lockfiles is resolved by regeneration; any other conflict skips
/// the member. The temp ref is created last, create-only, so a failure leaves none behind.
///
/// # Errors
///
/// Git could not prepare the checkout or create the temp ref.
pub fn build_candidate(
    repo: &Repo,
    primary: &Path,
    id: &str,
    base_oid: &str,
    members: &[CandidateMember],
) -> Result<Candidate, LandError> {
    let (dir, lock) = checkout_paths(repo.common_dir());
    let guard = crate::git::lock_exclusive(&lock)?;
    prepare_checkout(repo, primary, &dir, base_oid)?;
    let shared_files = lockfile::committed_shared_files(repo, base_oid)?;
    let (merged, skipped) = merge_all(repo, &dir, &shared_files, members)?;
    let oid = head(repo, &dir)?;
    let ref_name = format!("{TRAIN_REF_PREFIX}{id}");
    let zero = "0".repeat(oid.len());
    let set = git(repo, primary, &["update-ref", &ref_name, &oid, &zero])?;
    if !set.ok() {
        return Err(LandError::Config(format!(
            "could not create {ref_name}: {}",
            set.text
        )));
    }
    tracing::info!(%ref_name, %oid, merged = merged.len(), skipped = skipped.len(), "candidate built");
    Ok(Candidate {
        oid,
        merged,
        skipped,
        ref_name,
        primary: primary.to_path_buf(),
        checkout: dir,
        _guard: guard,
    })
}

/// The persistent train checkout and its lock file under the git common dir.
fn checkout_paths(common: &Path) -> (PathBuf, PathBuf) {
    let frob = common.join("frob");
    (
        frob.join(TRAIN_CHECKOUT_DIR),
        frob.join(format!("{TRAIN_CHECKOUT_DIR}.lock")),
    )
}

/// Move the persistent train checkout to `oid`, creating it on first use or when unusable.
fn prepare_checkout(repo: &Repo, primary: &Path, dir: &Path, oid: &str) -> Result<(), LandError> {
    let text = dir.to_string_lossy().into_owned();
    if dir.join(".git").exists() {
        let _ = git(repo, dir, &["merge", "--abort"]);
        let moved = git(
            repo,
            dir,
            &["checkout", "--detach", "--force", "--quiet", oid],
        );
        if moved.as_ref().is_ok_and(crate::git::GitRun::ok) {
            let _ = git(repo, dir, &["clean", "-fdq"]);
            tracing::info!(oid, dir = %dir.display(), "train checkout reused");
            return Ok(());
        }
        tracing::warn!(dir = %dir.display(), "train checkout unusable; recreating");
        let _ = git(repo, primary, &["worktree", "remove", "--force", &text]);
    }
    if dir.exists() {
        let _ = std::fs::remove_dir_all(dir);
    }
    let _ = git(repo, primary, &["worktree", "prune"]);
    let add = git(
        repo,
        primary,
        &["worktree", "add", "--detach", "--force", &text, oid],
    )?;
    if !add.ok() {
        return Err(LandError::Config(format!(
            "could not create the train checkout at {oid}: {}",
            add.text
        )));
    }
    tracing::info!(oid, dir = %dir.display(), "train checkout created");
    Ok(())
}

/// Merge `members` one by one in `dir`; returns the merged handles and the skips.
fn merge_all(
    repo: &Repo,
    dir: &Path,
    shared_files: &[String],
    members: &[CandidateMember],
) -> Result<(Vec<String>, Vec<Skipped>), LandError> {
    let mut merged = Vec::new();
    let mut skipped = Vec::new();
    for m in members {
        if let Some(reason) = moved_branch(repo, dir, m)? {
            tracing::warn!(handle = %m.handle, "skipped: {reason}");
            skipped.push(Skipped {
                handle: m.handle.clone(),
                reason,
            });
            continue;
        }
        match merge_one(repo, dir, shared_files, m)? {
            Ok(()) => {
                tracing::info!(handle = %m.handle, "merged into candidate");
                merged.push(m.handle.clone());
            }
            Err(reason) => {
                tracing::warn!(handle = %m.handle, "skipped, merge conflict: {reason}");
                skipped.push(Skipped {
                    handle: m.handle.clone(),
                    reason,
                });
            }
        }
    }
    Ok((merged, skipped))
}

/// Why `m` must not merge: its branch no longer points at the oid frozen at enqueue.
fn moved_branch(repo: &Repo, dir: &Path, m: &CandidateMember) -> Result<Option<String>, LandError> {
    let now = git(
        repo,
        dir,
        &[
            "rev-parse",
            "--verify",
            &format!("refs/heads/{}^{{commit}}", m.branch),
        ],
    )?;
    if now.ok() && now.text == m.oid {
        return Ok(None);
    }
    Ok(Some(format!(
        "branch {} moved since enqueue; re-run frob land",
        m.branch
    )))
}

/// Merge the frozen oid of `m`; the inner error is the reason it was skipped (merge aborted).
fn merge_one(
    repo: &Repo,
    dir: &Path,
    shared_files: &[String],
    m: &CandidateMember,
) -> Result<Result<(), String>, LandError> {
    let run = git(
        repo,
        dir,
        &[
            "-c",
            "user.name=frob",
            "-c",
            "user.email=frob@localhost",
            "merge",
            "--no-edit",
            &m.oid,
        ],
    )?;
    if run.ok() {
        return Ok(Ok(()));
    }
    let listed = git(repo, dir, &["diff", "--name-only", "--diff-filter=U"])?;
    let paths: Vec<String> = listed.text.lines().map(str::to_owned).collect();
    if lockfile::all_shared(shared_files, &paths)? {
        return match lockfile::resolve(repo, dir, &m.handle, &paths) {
            Ok(_) => Ok(Ok(())),
            // `resolve` aborted the merge itself.
            Err(e) => Ok(Err(e.to_string())),
        };
    }
    let _ = git(repo, dir, &["merge", "--abort"]);
    Ok(Err(run.text))
}

/// The oid of `HEAD` in `dir`.
fn head(repo: &Repo, dir: &Path) -> Result<String, LandError> {
    let run = git(repo, dir, &["rev-parse", "HEAD"])?;
    if run.ok() {
        Ok(run.text)
    } else {
        Err(LandError::Config(format!("rev-parse HEAD: {}", run.text)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sh(dir: &Path, args: &[&str]) -> String {
        let repo = Repo::discover(dir).expect("open");
        let mut full = vec!["-c", "user.name=t", "-c", "user.email=t@t"];
        full.extend_from_slice(args);
        let run = git(&repo, dir, &full).expect("git");
        assert!(run.ok(), "{args:?}: {}", run.text);
        run.text
    }

    /// A repo with `a.txt`/`b.txt` on main and one branch per `(name, file, content)`.
    fn fixture(branches: &[(&str, &str, &str)]) -> (tempfile::TempDir, Repo, String) {
        let dir = tempfile::tempdir().expect("tempdir");
        let repo = Repo::init(dir.path()).expect("init");
        let p = dir.path();
        std::fs::write(p.join("a.txt"), "a\n").expect("a");
        std::fs::write(p.join("b.txt"), "b\n").expect("b");
        sh(p, &["add", "."]);
        sh(p, &["commit", "-m", "base"]);
        let base = sh(p, &["rev-parse", "HEAD"]);
        for (name, file, content) in branches {
            sh(p, &["checkout", "-b", name, &base]);
            std::fs::write(p.join(file), content).expect("write");
            sh(p, &["commit", "-am", name]);
        }
        sh(p, &["checkout", "--detach", &base]);
        (dir, repo, base)
    }

    fn member(dir: &Path, handle: &str, file: &str) -> CandidateMember {
        let branch = format!("ticket-{handle}");
        CandidateMember {
            handle: handle.to_owned(),
            oid: sh(dir, &["rev-parse", &branch]),
            branch,
            scope: vec![file.to_owned()],
        }
    }

    fn refs(dir: &Path) -> String {
        sh(dir, &["for-each-ref", "refs/frob/train/"])
    }

    // frob:ticket 01M4Z1MYPEJ6HDVBJVPDVHR8MA
    // frob:tests crates/frob-land/src/candidate.rs::build_candidate
    #[test]
    fn a_conflicting_branch_is_skipped_and_the_rest_merged() {
        let (dir, repo, base) = fixture(&[
            ("ticket-x", "a.txt", "x\n"),
            ("ticket-y", "a.txt", "y\n"),
            ("ticket-z", "b.txt", "z\n"),
        ]);
        let ms = [
            member(dir.path(), "x", "a.txt"),
            member(dir.path(), "y", "a.txt"),
            member(dir.path(), "z", "b.txt"),
        ];
        let c = build_candidate(&repo, dir.path(), "t1", &base, &ms).expect("build");
        assert_eq!(c.merged, ["x", "z"]);
        assert_eq!(c.skipped.len(), 1);
        assert_eq!(c.skipped[0].handle, "y");
        assert_eq!(sh(dir.path(), &["rev-parse", c.ref_name()]), c.oid);
        assert_eq!(sh(dir.path(), &["show", &format!("{}:b.txt", c.oid)]), "z");
        assert_eq!(sh(dir.path(), &["show", &format!("{}:a.txt", c.oid)]), "x");
    }

    // frob:ticket 01M4Z1MYPEJ6HDVBJVPDVHR8MA
    // frob:tests crates/frob-land/src/candidate.rs::partition_trains
    #[test]
    fn overlapping_scopes_go_to_separate_trains() {
        let mk = |h: &str, g: &str| CandidateMember {
            handle: h.to_owned(),
            branch: format!("ticket-{h}"),
            oid: String::new(),
            scope: vec![g.to_owned()],
        };
        let ms = vec![mk("x", "src/a.rs"), mk("y", "src/**"), mk("z", "docs/b.md")];
        let trains = partition_trains(ms).expect("partition");
        let names: Vec<Vec<&str>> = trains
            .iter()
            .map(|t| t.iter().map(|m| m.handle.as_str()).collect())
            .collect();
        assert_eq!(names, [vec!["x", "z"], vec!["y"]]);
    }

    // frob:ticket 01M4Z1MYPEJ6HDVBJVPDVHR8MA
    // frob:tests crates/frob-land/src/candidate.rs::build_candidate
    #[test]
    fn disjoint_branches_merge_and_the_ref_goes_on_drop() {
        let (dir, repo, base) =
            fixture(&[("ticket-x", "a.txt", "x\n"), ("ticket-z", "b.txt", "z\n")]);
        let ms = [
            member(dir.path(), "x", "a.txt"),
            member(dir.path(), "z", "b.txt"),
        ];
        let c = build_candidate(&repo, dir.path(), "t2", &base, &ms).expect("build");
        assert_eq!(c.merged, ["x", "z"]);
        assert!(refs(dir.path()).contains("refs/frob/train/t2"));
        drop(c);
        assert_eq!(refs(dir.path()), "");
    }

    // frob:ticket 01M4Z1MYPEJ6HDVBJVPDVHR8MA
    // frob:tests crates/frob-land/src/candidate.rs::build_candidate
    #[test]
    fn a_failure_leaves_no_temp_ref() {
        let (dir, repo, _base) = fixture(&[("ticket-x", "a.txt", "x\n")]);
        let ms = [member(dir.path(), "x", "a.txt")];
        let err = build_candidate(
            &repo,
            dir.path(),
            "t3",
            "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
            &ms,
        );
        assert!(err.is_err());
        assert_eq!(refs(dir.path()), "");
    }

    // frob:ticket 01M4Z1MYPEJ6HDVBJVPDVHR8MA
    // frob:tests crates/frob-land/src/candidate.rs::moved_branch
    #[test]
    fn a_branch_that_moved_since_enqueue_is_skipped() {
        let (dir, repo, base) = fixture(&[("ticket-x", "a.txt", "x\n")]);
        let m = member(dir.path(), "x", "a.txt");
        sh(dir.path(), &["checkout", "ticket-x"]);
        std::fs::write(dir.path().join("a.txt"), "x2\n").expect("write");
        sh(dir.path(), &["commit", "-am", "more"]);
        sh(dir.path(), &["checkout", "--detach", &base]);
        let c = build_candidate(&repo, dir.path(), "t4", &base, &[m]).expect("build");
        assert!(c.merged.is_empty());
        assert!(c.skipped[0].reason.contains("moved since enqueue"));
        assert_eq!(c.oid, base);
    }

    // frob:ticket 01M4Z1MYPEJ6HDVBJVPDVHR8MA
    // frob:tests crates/frob-land/src/candidate.rs::merge_one
    #[test]
    fn disjoint_tickets_that_both_change_cargo_lock_merge() {
        let dir = tempfile::tempdir().expect("tempdir");
        let repo = Repo::init(dir.path()).expect("init");
        let p = dir.path();
        std::fs::write(
            p.join("frob.toml"),
            "[lease]\nshared_files = [\"Cargo.lock\"]\n",
        )
        .expect("toml");
        std::fs::write(
            p.join("Cargo.toml"),
            "[package]\nname = \"p\"\nversion = \"0.1.0\"\nedition = \"2021\"\n[lib]\npath = \"l.rs\"\n",
        )
        .expect("manifest");
        std::fs::write(p.join("l.rs"), "").expect("lib");
        std::fs::write(
            p.join("Cargo.lock"),
            "# base\nversion = 4\n\n[[package]]\nname = \"p\"\nversion = \"0.1.0\"\n",
        )
        .expect("lock");
        std::fs::write(p.join("a.txt"), "a\n").expect("a");
        std::fs::write(p.join("b.txt"), "b\n").expect("b");
        sh(p, &["add", "."]);
        sh(p, &["commit", "-m", "base"]);
        let base = sh(p, &["rev-parse", "HEAD"]);
        for (name, file) in [("ticket-x", "a.txt"), ("ticket-z", "b.txt")] {
            sh(p, &["checkout", "-b", name, &base]);
            std::fs::write(p.join(file), "changed\n").expect("write");
            std::fs::write(
                p.join("Cargo.lock"),
                format!(
                    "# {name}\nversion = 4\n\n[[package]]\nname = \"p\"\nversion = \"0.1.0\"\n"
                ),
            )
            .expect("lock");
            sh(p, &["commit", "-am", name]);
        }
        sh(p, &["checkout", "--detach", &base]);
        let ms = [member(p, "x", "a.txt"), member(p, "z", "b.txt")];
        let c = build_candidate(&repo, p, "t5", &base, &ms).expect("build");
        assert_eq!(c.merged, ["x", "z"], "{:?}", c.skipped);
    }
}
