//! Post-merge hunk-presence check: a ticket's own added lines must survive the pre-land base merge
//! (frob:ticket 01M3AXSDBMG2ZAEHTQ6JHA8CYK).
//!
//! When a stacked predecessor squash-lands, the base carries a rewrite of the same regions and the
//! merge of the base into the successor can resolve the successor's adjacent hunks away while the
//! feature commit stays an ancestor. Ancestry then says the work is there and the tree says it is
//! not. [`dropped_hunks`] compares, per file, the lines the ticket's own commits added and that the
//! pre-merge tree held against the merged tree, and names every commit that lost lines.

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use gob_git::Repo;
use gob_path::Shown;
use schemars::JsonSchema;
use serde::Serialize;

use crate::error::{LandError, needs_action};
use crate::git::git;

/// Lines of one file a merge dropped, with the ticket commit that added them.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct DroppedHunk {
    /// The ticket commit that added the lines.
    pub commit: String,
    /// Repo-relative path of the file.
    pub path: String,
    /// The added lines that are gone from the merged tree (trimmed, first few only).
    pub lines: Vec<String>,
}

/// Most dropped lines quoted per hunk in a refusal.
const QUOTED_LINES: usize = 3;

/// Added lines per file parsed from `git show -U0` output (`+` lines, trimmed, blanks skipped).
fn parse_added(diff: &str) -> BTreeMap<String, Vec<String>> {
    let mut out: BTreeMap<String, Vec<String>> = BTreeMap::new();
    let mut file: Option<String> = None;
    for line in diff.lines() {
        if let Some(p) = line.strip_prefix("+++ b/") {
            file = Some(p.to_owned());
        } else if line.starts_with("+++ ") || line.starts_with("--- ") {
            if line.starts_with("+++ /dev/null") {
                file = None;
            }
        } else if let (Some(f), Some(added)) = (&file, line.strip_prefix('+')) {
            let t = added.trim();
            if !t.is_empty() {
                out.entry(f.clone()).or_default().push(t.to_owned());
            }
        }
    }
    out
}

/// The trimmed non-empty lines of `rev:path`, or none when the file is absent there.
fn lines_at(repo: &Repo, wt: &Path, rev: &str, path: &str) -> Result<BTreeSet<String>, LandError> {
    let run = git(repo, wt, &["show", &format!("{rev}:{path}")])?;
    if !run.ok() {
        return Ok(BTreeSet::new());
    }
    Ok(run
        .text
        .lines()
        .map(|l| l.trim().to_owned())
        .filter(|l| !l.is_empty())
        .collect())
}

/// The ticket's own added lines (premerge tip `pre`, against `base`) that `merged` lost, one entry per commit and file.
///
/// Own commits are the non-merge commits of `base..pre` whose patch is not already on the base
/// (`--cherry-pick`), minus `chore(tickets)` commits; a line the base already carries is a passenger
/// and never counts as dropped.
///
/// # Errors
/// Git failed to list or show the commits.
pub fn dropped_hunks(
    repo: &Repo,
    wt: &Path,
    base: &str,
    pre: &str,
    merged: &str,
) -> Result<Vec<DroppedHunk>, LandError> {
    let range = format!("{base}...{pre}");
    let revs = git(
        repo,
        wt,
        &[
            "rev-list",
            "--no-merges",
            "--right-only",
            "--cherry-pick",
            "--reverse",
            "--format=%H %s",
            &range,
        ],
    )?;
    if !revs.ok() {
        return Err(LandError::Config(format!(
            "git rev-list {range}: {}",
            revs.text
        )));
    }
    let mut dropped = Vec::new();
    for entry in revs.text.lines().filter(|l| !l.starts_with("commit ")) {
        let (sha, subject) = entry.split_once(' ').unwrap_or((entry, ""));
        if subject.starts_with("chore(tickets)") {
            continue;
        }
        let show = git(repo, wt, &["show", "--format=", "-U0", "--no-color", sha])?;
        for (path, added) in parse_added(&show.text) {
            let before = lines_at(repo, wt, pre, &path)?;
            let after = lines_at(repo, wt, merged, &path)?;
            let on_base = lines_at(repo, wt, base, &path)?;
            let lost: Vec<String> = added
                .into_iter()
                .filter(|l| before.contains(l) && !after.contains(l) && !on_base.contains(l))
                .take(QUOTED_LINES)
                .collect();
            if !lost.is_empty() {
                tracing::warn!(commit = sha, %path, lost = lost.len(), "merge dropped ticket lines");
                dropped.push(DroppedHunk {
                    commit: sha.to_owned(),
                    path,
                    lines: lost,
                });
            }
        }
    }
    Ok(dropped)
}

// frob:ticket 01M5EBD66SH12P69KWVXA8K2NC
/// Hunks that past base merges on the branch ending at `head` dropped (`frob train status` audit).
///
/// Each first-parent merge commit `M` of `base..head` is checked as a land-time merge would be:
/// `M^1` is the premerge tip, `M^2` the base side, `M` the merged tree; results are concatenated
/// oldest merge first.
///
/// # Errors
/// Git failed to list the merges or show their commits.
pub fn audit_merges(
    repo: &Repo,
    wt: &Path,
    base: &str,
    head: &str,
) -> Result<Vec<DroppedHunk>, LandError> {
    let range = format!("{base}..{head}");
    let merges = git(
        repo,
        wt,
        &[
            "rev-list",
            "--merges",
            "--first-parent",
            "--reverse",
            &range,
        ],
    )?;
    if !merges.ok() {
        return Err(LandError::Config(format!(
            "git rev-list {range}: {}",
            merges.text
        )));
    }
    let mut out = Vec::new();
    for merge in merges.text.lines().map(str::trim).filter(|l| !l.is_empty()) {
        out.extend(dropped_hunks(
            repo,
            wt,
            &format!("{merge}^2"),
            &format!("{merge}^1"),
            merge,
        )?);
    }
    Ok(out)
}

/// Refuse (`E-LAND-HUNKS-DROPPED`) when the base merge at `merged` lost lines the ticket's commits added.
pub(crate) fn verify_after_merge(
    repo: &Repo,
    wt: &Path,
    base: &str,
    pre: &str,
    merged: &str,
    handle: &str,
) -> Result<(), LandError> {
    let dropped = dropped_hunks(repo, wt, base, pre, merged)?;
    if dropped.is_empty() {
        tracing::info!(pre, merged, "every ticket hunk survived the base merge");
        return Ok(());
    }
    let mut commits: Vec<&str> = dropped.iter().map(|d| d.commit.as_str()).collect();
    commits.dedup();
    let detail: Vec<String> = dropped
        .iter()
        .map(|d| {
            let short = d.commit.get(..10).unwrap_or(&d.commit);
            format!("{short} {}: `{}`", d.path, d.lines.join("` / `"))
        })
        .collect();
    Err(needs_action(
        "E-LAND-HUNKS-DROPPED",
        format!(
            "merging {base} dropped ticket lines (merge commit {merged}): {}",
            detail.join("; ")
        ),
        format!(
            "git -C {} reset --hard {pre}, then merge {base} resolving those hunks by hand (or: git -C {} cherry-pick -n {}), then frob land {handle}",
            Shown::of(wt),
            Shown::of(wt),
            commits.join(" ")
        ),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(repo: &Repo, dir: &Path, args: &[&str]) -> String {
        let r = git(repo, dir, args).expect("spawn git");
        assert!(r.ok(), "git {args:?}: {}", r.text);
        r.text
    }

    fn commit_file(repo: &Repo, dir: &Path, name: &str, body: &str, msg: &str) {
        std::fs::write(dir.join(name), body).expect("write");
        run(repo, dir, &["add", name]);
        run(repo, dir, &["commit", "-q", "-m", msg]);
    }

    fn fixture() -> (tempfile::TempDir, Repo) {
        let tmp = tempfile::tempdir().expect("tempdir");
        let repo = Repo::init(tmp.path()).expect("init");
        let d = tmp.path();
        run(&repo, d, &["config", "user.name", "T"]);
        run(&repo, d, &["config", "user.email", "t@example.com"]);
        run(&repo, d, &["checkout", "-q", "-b", "dev"]);
        commit_file(&repo, d, "m.txt", "a\nb\nc\nd\ne\nf\n", "base");
        // A1 then A2 stacked on A1.
        run(&repo, d, &["checkout", "-q", "-b", "a1"]);
        commit_file(&repo, d, "m.txt", "a\nB1\nc\nd\ne\nf\n", "a1");
        run(&repo, d, &["checkout", "-q", "-b", "a2"]);
        commit_file(&repo, d, "m.txt", "a\nB1\nc\nd\ne2\nf\n", "a2 feature");
        // Squash-land A1 on dev.
        run(&repo, d, &["checkout", "-q", "dev"]);
        run(&repo, d, &["merge", "-q", "--squash", "a1"]);
        run(&repo, d, &["commit", "-q", "-m", "a1 squashed"]);
        run(&repo, d, &["checkout", "-q", "a2"]);
        (tmp, repo)
    }

    // frob:ticket 01M3AXSDBMG2ZAEHTQ6JHA8CYK
    // frob:tests crates/frob-land/src/hunk_presence.rs::dropped_hunks
    #[test]
    fn a_stacked_successor_keeps_its_hunks_after_its_base_squash_lands() {
        let (tmp, repo) = fixture();
        let d = tmp.path();
        let pre = run(&repo, d, &["rev-parse", "HEAD"]);
        run(&repo, d, &["merge", "-q", "--no-edit", "dev"]);
        let merged = run(&repo, d, &["rev-parse", "HEAD"]);
        let dropped = dropped_hunks(&repo, d, "dev", &pre, &merged).expect("check");
        assert!(dropped.is_empty(), "{dropped:?}");
        verify_after_merge(&repo, d, "dev", &pre, &merged, "~X").expect("clean merge passes");
    }

    // frob:ticket 01M3AXSDBMG2ZAEHTQ6JHA8CYK
    // frob:tests crates/frob-land/src/hunk_presence.rs::verify_after_merge
    #[test]
    fn a_merge_that_resolves_the_successor_away_is_refused_with_the_commit() {
        let (tmp, repo) = fixture();
        let d = tmp.path();
        let pre = run(&repo, d, &["rev-parse", "HEAD"]);
        run(&repo, d, &["merge", "-q", "--no-edit", "-s", "ours", "dev"]);
        let merged = run(&repo, d, &["rev-parse", "HEAD"]);
        // `ours` keeps the successor; force the drop by restoring dev's file content.
        run(&repo, d, &["checkout", "dev", "--", "m.txt"]);
        run(&repo, d, &["commit", "-q", "--amend", "--no-edit"]);
        let merged2 = run(&repo, d, &["rev-parse", "HEAD"]);
        assert_ne!(merged, merged2);
        let err = verify_after_merge(&repo, d, "dev", &pre, &merged2, "~X").expect_err("drop");
        let r = err.refusal().expect("refusal");
        assert_eq!(r.code, "E-LAND-HUNKS-DROPPED");
        assert!(r.message.contains("e2"), "{}", r.message);
    }

    // frob:ticket 01M5EBD66SH12P69KWVXA8K2NC
    // frob:tests crates/frob-land/src/hunk_presence.rs::audit_merges
    #[test]
    fn audit_finds_a_past_merge_that_dropped_hunks_and_passes_a_clean_one() {
        let (tmp, repo) = fixture();
        let d = tmp.path();
        run(&repo, d, &["merge", "-q", "--no-edit", "dev"]);
        let clean = run(&repo, d, &["rev-parse", "HEAD"]);
        assert!(
            audit_merges(&repo, d, "dev", &clean)
                .expect("audit")
                .is_empty()
        );
        // A second, lossy merge: reset to before the clean merge and redo it dropping the lines.
        run(&repo, d, &["reset", "-q", "--hard", "HEAD^1"]);
        run(&repo, d, &["merge", "-q", "--no-edit", "-s", "ours", "dev"]);
        run(&repo, d, &["checkout", "dev", "--", "m.txt"]);
        run(&repo, d, &["commit", "-q", "--amend", "--no-edit"]);
        let lossy = run(&repo, d, &["rev-parse", "HEAD"]);
        let found = audit_merges(&repo, d, "dev", &lossy).expect("audit");
        assert!(
            found.iter().any(|h| h.lines.iter().any(|l| l == "e2")),
            "{found:?}"
        );
    }
}
