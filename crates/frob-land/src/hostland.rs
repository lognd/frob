//! Hosting-side lands: a ticket merged by squash or rebase in the hosting UI is recognised and recorded (distributed-tickets.md rows 46 and 47, DT22).
//!
//! frob's own lands are fast-forward or merge, so the ticket tip is in base. A
//! squash or rebase merge on the host leaves no such tie; the commit message
//! still carries a `Frob-Ticket: <ULID>` trailer. [`record_host_lands`] scans a
//! base ref for those trailers and, for every in-progress ticket found, records
//! a `land` event at the merging commit and closes the ticket as done.
//!
//! A merge with no trailer is matched by patch id: the ticket branch's whole
//! diff against its merge-base is fingerprinted (hunk positions and whitespace
//! ignored, as `git patch-id` does) and compared with each commit that landed
//! on the base since; an equal fingerprint is a squash or single-commit rebase.

use std::collections::BTreeMap;
use std::hash::{DefaultHasher, Hash, Hasher};

use frob_ledger::event::EventBody;
use frob_ledger::index::ListFilter;
use frob_ledger::model::{Category, Outcome};
use frob_ledger::{Ledger, TicketId};

use crate::error::LandError;
use crate::events::{LandEvent, append_land};
use crate::git::git;

/// The commit trailer naming the ticket a commit belongs to.
const TRAILER_KEY: &str = "Frob-Ticket";

/// Separator between a commit id and its trailer values in the log format.
const FIELD_SEP: char = '\u{1f}';

/// A ticket recognised as landed by the host.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HostLand {
    /// The ticket.
    pub id: TicketId,
    /// Its handle, for messages.
    pub handle: String,
    /// The commit on the base ref that carries the ticket's trailer.
    pub commit: String,
}

/// Record separator between commits in the `git log -p` output used for patch-id matching.
const RECORD_SEP: char = '\u{1e}';

/// Most commits on the base scanned for a patch-id match, bounding cost on long histories.
const PATCH_SCAN_LIMIT: &str = "--max-count=500";

/// A whitespace- and position-insensitive fingerprint of a unified diff (`git patch-id` in spirit); `None` for an empty change.
// frob:ticket 01M5DT8FKY9HJW3R9Q4CZB283M
fn patch_fingerprint(diff: &str) -> Option<u64> {
    let mut hasher = DefaultHasher::new();
    let mut any = false;
    for line in diff.lines() {
        if !(line.starts_with('+') || line.starts_with('-')) {
            continue;
        }
        let squeezed: String = line.chars().filter(|c| !c.is_whitespace()).collect();
        squeezed.hash(&mut hasher);
        any = true;
    }
    any.then(|| hasher.finish())
}

/// The newest commit in `git log -p` output (records led by [`RECORD_SEP`] and the sha) whose diff fingerprints to `target`.
// frob:ticket 01M5DT8FKY9HJW3R9Q4CZB283M
fn find_patch_match(log: &str, target: u64) -> Option<String> {
    log.split(RECORD_SEP).find_map(|record| {
        let (sha, diff) = record.split_once('\n')?;
        (patch_fingerprint(diff) == Some(target)).then(|| sha.trim().to_owned())
    })
}

/// The commit on `base_ref` whose change equals the whole change of `ticket/<handle>`, when the branch still exists.
// frob:ticket 01M5DT8FKY9HJW3R9Q4CZB283M
fn patch_match(repo: &gob_git::Repo, handle: &str, base_ref: &str) -> Result<Option<String>, LandError> {
    let cwd = repo.work_dir().unwrap_or_else(|| repo.common_dir());
    let name = handle.trim_start_matches('~');
    let tip = [
        format!("refs/heads/ticket/{name}"),
        format!("refs/remotes/origin/ticket/{name}"),
    ]
    .into_iter()
    .find(|r| repo.rev_parse(r).is_ok());
    let Some(tip) = tip else {
        return Ok(None);
    };
    let Ok(Some(mb)) = repo.merge_base(&tip, base_ref) else {
        return Ok(None);
    };
    let mb = mb.to_string();
    let diff = git(
        repo,
        cwd,
        &["diff", "-U0", "--no-color", "--no-ext-diff", "--no-renames", &mb, &tip],
    )?;
    if !diff.ok() {
        return Ok(None);
    }
    let Some(target) = patch_fingerprint(&diff.text) else {
        return Ok(None);
    };
    let range = format!("{mb}..{base_ref}");
    let log = git(
        repo,
        cwd,
        &[
            "log",
            "-p",
            "-U0",
            "--no-color",
            "--no-ext-diff",
            "--no-renames",
            "--no-merges",
            PATCH_SCAN_LIMIT,
            "--format=%x1e%H",
            &range,
        ],
    )?;
    if !log.ok() {
        return Ok(None);
    }
    let found = find_patch_match(&log.text, target);
    tracing::debug!(handle, found = ?found, "patch-id scan");
    Ok(found)
}

/// Map each trailer ULID to the newest commit carrying it, from `git log` output of `<sha> US <values>` lines (newest first).
fn parse_trailer_log(text: &str) -> BTreeMap<String, String> {
    let mut found = BTreeMap::new();
    for line in text.lines() {
        let Some((sha, values)) = line.split_once(FIELD_SEP) else {
            continue;
        };
        for ulid in values.split(',').map(str::trim).filter(|v| !v.is_empty()) {
            found
                .entry(ulid.to_owned())
                .or_insert_with(|| sha.trim().to_owned());
        }
    }
    found
}

/// Record a `land` event and close every in-progress ticket whose `Frob-Ticket` trailer (or, lacking one, whose branch's patch) appears on `base_ref`'s history; returns what was recorded.
///
/// `base` is the short base branch name (for the recorded `base_ref`); a
/// `base_ref` that does not resolve yields nothing. Idempotent: a ticket
/// already done is skipped.
///
/// # Errors
///
/// Ledger and git failures.
// frob:ticket 01M5CW0609NX9MJ45G2R4CQE0R
pub fn record_host_lands(
    ledger: &Ledger,
    base: &str,
    base_ref: &str,
) -> Result<Vec<HostLand>, LandError> {
    let repo = ledger.repo();
    if repo.rev_parse(base_ref).is_err() {
        tracing::info!(base_ref, "no base ref to scan for host lands");
        return Ok(Vec::new());
    }
    let pending = ledger.list(&ListFilter {
        category: Some(Category::InProgress),
        ..ListFilter::default()
    })?;
    if pending.is_empty() {
        return Ok(Vec::new());
    }
    let format =
        format!("--format=%H{FIELD_SEP}%(trailers:key={TRAILER_KEY},valueonly,separator=%x2c)");
    let grep = format!("--grep=^{TRAILER_KEY}: ");
    let run = git(
        repo,
        repo.work_dir().unwrap_or_else(|| repo.common_dir()),
        &["log", &format, &grep, base_ref],
    )?;
    if !run.ok() {
        return Err(LandError::Config(format!(
            "git log {base_ref} failed: {}",
            run.text
        )));
    }
    let by_ulid = parse_trailer_log(&run.text);
    let mut recorded = Vec::new();
    for s in pending {
        let handle = s.handle.clone();
        let commit = match by_ulid.get(&s.id.to_string()) {
            Some(c) => c.clone(),
            None => match patch_match(repo, &handle, base_ref)? {
                Some(c) => {
                    tracing::info!(handle = %handle, commit = %c, "matched a host merge by patch id");
                    c
                }
                None => continue,
            },
        };
        let commit = &commit;
        let already = ledger
            .events(s.id)?
            .iter()
            .any(|e| matches!(e.body, EventBody::Land(_)));
        if !already {
            append_land(
                ledger,
                s.id,
                &LandEvent {
                    base_ref: &format!("refs/heads/{base}"),
                    commit,
                    branch: &format!("ticket/{}", handle.trim_start_matches('~')),
                    pushed: true,
                },
            )?;
        }
        ledger.close(
            s.id,
            Some(Outcome::Done),
            Some(format!("merged on the host (squash or rebase) at {commit}")),
            &[],
        )?;
        tracing::info!(ticket = %s.id, handle = %handle, commit = %commit, "recorded a hosting-side land");
        recorded.push(HostLand {
            id: s.id,
            handle,
            commit: commit.clone(),
        });
    }
    Ok(recorded)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests parse_trailer_log
    #[test]
    fn the_newest_commit_wins_and_blank_trailers_are_skipped() {
        let log = "aaa\u{1f}01ABC\nbbb\u{1f}\nccc\u{1f}01ABC,01DEF\n";
        let m = parse_trailer_log(log);
        assert_eq!(m.get("01ABC").map(String::as_str), Some("aaa"));
        assert_eq!(m.get("01DEF").map(String::as_str), Some("ccc"));
        assert_eq!(m.len(), 2);
    }

    // frob:tests patch_fingerprint
    #[test]
    fn a_fingerprint_ignores_hunk_positions_and_whitespace() {
        let a = "diff --git a/x b/x\nindex 1..2\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-old\n+new  line\n";
        let b = "--- a/x\n+++ b/x\n@@ -40 +41 @@\n-old\n+new line\n";
        assert_eq!(patch_fingerprint(a), patch_fingerprint(b));
        assert!(patch_fingerprint(a).is_some());
        assert_eq!(patch_fingerprint("diff --git a/x b/x\n"), None);
    }

    // frob:tests find_patch_match
    #[test]
    fn the_newest_equal_patch_is_found() {
        let diff = "--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n";
        let other = "--- a/y\n+++ b/y\n@@ -1 +1 @@\n-a\n+b\n";
        let log = format!("\u{1e}n1\n{other}\u{1e}n2\n{diff}\u{1e}n3\n{diff}");
        let target = patch_fingerprint(diff).expect("fp");
        assert_eq!(find_patch_match(&log, target).as_deref(), Some("n2"));
        assert_eq!(find_patch_match("", target), None);
    }
}
