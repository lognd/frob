//! Hosting-side lands: a ticket merged by squash or rebase in the hosting UI is recognised and recorded (distributed-tickets.md rows 46 and 47, DT22).
//!
//! frob's own lands are fast-forward or merge, so the ticket tip is in base. A
//! squash or rebase merge on the host leaves no such tie; the commit message
//! still carries a `Frob-Ticket: <ULID>` trailer. [`record_host_lands`] scans a
//! base ref for those trailers and, for every in-progress ticket found, records
//! a `land` event at the merging commit and closes the ticket as done.
//! Matching by patch id is a follow-up.

use std::collections::BTreeMap;

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

/// Record a `land` event and close every in-progress ticket whose `Frob-Ticket` trailer appears on `base_ref`'s history; returns what was recorded.
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
        let Some(commit) = by_ulid.get(&s.id.to_string()) else {
            continue;
        };
        let handle = s.handle.clone();
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

    // frob:tests crates/frob-land/src/hostland.rs::parse_trailer_log
    #[test]
    fn the_newest_commit_wins_and_blank_trailers_are_skipped() {
        let log = "aaa\u{1f}01ABC\nbbb\u{1f}\nccc\u{1f}01ABC,01DEF\n";
        let m = parse_trailer_log(log);
        assert_eq!(m.get("01ABC").map(String::as_str), Some("aaa"));
        assert_eq!(m.get("01DEF").map(String::as_str), Some("ccc"));
        assert_eq!(m.len(), 2);
    }
}
