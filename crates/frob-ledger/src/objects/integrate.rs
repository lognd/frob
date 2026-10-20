//! Integrate a fetched ledger tip into the local ledger ref without a work tree (`distributed-tickets.md` section 4.6).
//!
//! Events are append-only files, so the union of both sides is the truth: new event files are
//! added, ticket documents that both sides changed are re-folded from the event union, and the
//! result is written as a two-parent commit by tree edit plus compare-and-swap. A fold or parse
//! failure, or a path both sides changed with no event cause, is reported as a [`Conflict`] and the
//! ref does not move (the integrity gate).

// frob:ticket 01M5CW049SPSRGGP5ENQD7BPB3

use std::collections::BTreeMap;

use gob_git::{ChangeKind, CommitOptions, Oid, RelPath, TreeRef};

use crate::doc;
use crate::error::{LedgerError, Result};
use crate::event::Event;
use crate::id::{EventId, TicketId};
use crate::layout;
use crate::ledger::Ledger;
use crate::merge::merged_document;

/// Generated files a divergent edit never needs a human for: ours is kept.
const KEEP_OURS: [&str; 2] = ["README.md", ".gitattributes"];

/// One path the integration could not resolve, with why.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Conflict {
    /// Repo-relative path.
    pub path: String,
    /// Human-readable cause.
    pub reason: String,
}

/// What integrating a remote tip did to the local ledger ref.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Integration {
    /// Local already contains the remote tip (equal or ahead).
    Unchanged,
    /// The local ref did not exist and now points at the remote tip.
    Created(Oid),
    /// The local ref moved forward to the remote tip.
    FastForward(Oid),
    /// A merge commit united both sides.
    Merged {
        /// The merge commit.
        commit: Oid,
        /// Event files added from the remote side.
        events: usize,
        /// Ticket documents re-folded from the event union.
        refolded: usize,
    },
    /// The sides cannot be united automatically; the ref did not move.
    Conflicts(Vec<Conflict>),
}

/// `.events/<ticket>/<event>.toml` split into its ids, when `path` has that shape.
fn event_path_ids(path: &str) -> Option<(TicketId, EventId)> {
    let rest = path.strip_prefix(".events/")?;
    let (tid, file) = rest.split_once('/')?;
    let stem = file.strip_suffix(".toml")?;
    Some((tid.parse().ok()?, stem.parse().ok()?))
}

/// Whether `path` is any object event file (`.../events/<x>.toml` or `.events/...`).
fn is_event_file(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("toml"))
        && (path.starts_with(".events/") || path.contains("/events/"))
}

fn conflict(path: &str, reason: impl Into<String>) -> Conflict {
    Conflict {
        path: path.to_owned(),
        reason: reason.into(),
    }
}

impl Ledger {
    /// Bring `theirs_ref` (a fetched tracking ref) into `ours_ref` by plumbing alone.
    ///
    /// Fast-forwards, creates a missing local ref, or unions a divergent history; never touches a
    /// work tree and never moves the ref when the result would not fold.
    ///
    /// # Errors
    ///
    /// Git failures, including a lost compare-and-swap (the caller re-integrates).
    // frob:ticket 01M5CW049SPSRGGP5ENQD7BPB3
    pub fn integrate(&self, ours_ref: &str, theirs_ref: &str) -> Result<Integration> {
        let theirs = self.repo.rev_parse(theirs_ref)?;
        let Some(ours) = self.tip_of(ours_ref)? else {
            self.repo
                .create_ref(ours_ref, theirs, "frob refresh: create ledger ref")?;
            tracing::info!(ours_ref, %theirs, "local ledger ref created from the remote");
            return Ok(Integration::Created(theirs));
        };
        if ours == theirs {
            return Ok(Integration::Unchanged);
        }
        let base = self
            .repo
            .merge_base(&ours.to_string(), &theirs.to_string())?;
        if base == Some(theirs) {
            tracing::debug!(%ours, %theirs, "local ledger is ahead; nothing to integrate");
            return Ok(Integration::Unchanged);
        }
        if base == Some(ours) {
            self.repo
                .update_ref_cas(ours_ref, Some(ours), theirs, "frob refresh: fast-forward")?;
            return Ok(Integration::FastForward(theirs));
        }
        self.merge_diverged(ours_ref, ours, theirs, base)
    }

    fn merge_diverged(
        &self,
        ours_ref: &str,
        ours: Oid,
        theirs: Oid,
        base: Option<Oid>,
    ) -> Result<Integration> {
        let (ours_sha, theirs_sha) = (ours.to_string(), theirs.to_string());
        let base_sha = base.map(|b| b.to_string());
        let changed = match base {
            Some(b) => self
                .repo
                .diff_names(&TreeRef::Oid(b), &TreeRef::Oid(theirs))?,
            None => self
                .repo
                .diff_names(&TreeRef::Oid(ours), &TreeRef::Oid(theirs))?,
        };
        let blob =
            |rev: &str, p: &str| -> Result<Option<Vec<u8>>> { Ok(self.repo.read_blob_at(rev, p)?) };
        let mut plan: BTreeMap<String, Option<Vec<u8>>> = BTreeMap::new();
        let mut conflicts = Vec::new();
        let (mut events, mut refolded) = (0, 0);
        for ch in &changed {
            let p = ch.path.as_str();
            let theirs_blob = blob(&theirs_sha, p)?;
            let ours_blob = blob(&ours_sha, p)?;
            if ours_blob == theirs_blob {
                continue;
            }
            if is_event_file(p) {
                match (ours_blob, ch.kind) {
                    (None, ChangeKind::Added | ChangeKind::Modified) => {
                        if let Err(why) = check_event(p, theirs_blob.as_deref()) {
                            conflicts.push(conflict(p, why));
                            continue;
                        }
                        plan.insert(p.to_owned(), theirs_blob);
                        events += 1;
                    }
                    _ => conflicts.push(conflict(p, "event file differs on both sides")),
                }
                continue;
            }
            let base_blob = match &base_sha {
                Some(rev) => blob(rev, p)?,
                None => None,
            };
            if ours_blob == base_blob {
                plan.insert(p.to_owned(), theirs_blob);
                continue;
            }
            if KEEP_OURS.contains(&p) {
                continue;
            }
            let ours_text =
                String::from_utf8_lossy(&ours_blob.clone().unwrap_or_default()).into_owned();
            let Some(id) = layout::peek_ticket_id(&ours_text) else {
                conflicts.push(conflict(
                    p,
                    "changed on both sides and not a ticket document",
                ));
                continue;
            };
            match self.refold(&ours_sha, &theirs_sha, id) {
                Ok(text) => {
                    plan.insert(p.to_owned(), Some(text.into_bytes()));
                    refolded += 1;
                }
                Err(e) => conflicts.push(conflict(p, format!("fold failed: {e}"))),
            }
        }
        if !conflicts.is_empty() {
            tracing::warn!(
                count = conflicts.len(),
                "ledger integration blocked by conflicts"
            );
            return Ok(Integration::Conflicts(conflicts));
        }
        let mut rel = Vec::with_capacity(plan.len());
        for (path, bytes) in plan {
            rel.push((RelPath::new(path)?, bytes));
        }
        let opts = CommitOptions {
            cas_retries: self.cfg.cas_retries,
            author: None,
        };
        let commit = self.repo.commit_merge(
            ours_ref,
            ours,
            theirs,
            &rel,
            "frob refresh: union merge of the ledger",
            &opts,
        )?;
        tracing::info!(%commit, events, refolded, "ledger merged by union");
        Ok(Integration::Merged {
            commit,
            events,
            refolded,
        })
    }

    /// The document text of ticket `id` folded from the union of both tips' events.
    fn refold(&self, ours: &str, theirs: &str, id: TicketId) -> Result<String> {
        let disk = self.read_events_at(ours, id)?;
        let extra = self.read_events_at(theirs, id)?;
        let (text, report) = merged_document(id, disk, extra)?;
        tracing::debug!(ticket = %id, events = report.events, from_theirs = report.from_extra, "refolded");
        doc::parse("merged", &text).map_err(|e| LedgerError::invalid(e.to_string()))?;
        Ok(text)
    }
}

/// Parse the added event file at `path`; an `Err` carries the reason.
fn check_event(path: &str, bytes: Option<&[u8]>) -> std::result::Result<(), String> {
    let Some(bytes) = bytes else {
        return Err("event file deleted on the remote".to_owned());
    };
    let text = std::str::from_utf8(bytes).map_err(|e| e.to_string())?;
    let Some((_, eid)) = event_path_ids(path) else {
        // Other object kinds are validated by their own folds; only names are checked here.
        return Ok(());
    };
    Event::parse(eid, text)
        .map(|_| ())
        .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob-ledger/src/objects/integrate.rs::event_path_ids
    #[test]
    fn event_paths_are_recognised() {
        let t = "01M5CW049SPSRGGP5ENQD7BPB3";
        assert!(event_path_ids(&format!(".events/{t}/{t}.toml")).is_some());
        assert!(event_path_ids("a/b.md").is_none());
        assert!(is_event_file("_cycles/x/events/y.toml"));
        assert!(is_event_file(".events/a/b.toml"));
        assert!(!is_event_file("a/events.md"));
    }
}
