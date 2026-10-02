//! The ledger merge driver: union the event files, re-fold the frontmatter.
//!
//! Git invokes `frob merge-driver %O %A %B %P` for a conflicted `ticket.md`.
//! The driver never picks a side: events are append-only files, so the union
//! of every event file reachable for the ticket is the truth, and the
//! frontmatter is its fold (tickets.md section 2).

use std::path::{Path, PathBuf};

use crate::doc;
use crate::error::{LedgerError, Result};
use crate::event::Event;
use crate::fold::fold;
use crate::id::{EventId, TicketId};

/// What a merge resolved.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MergeReport {
    /// The ticket.
    pub ticket: TicketId,
    /// Events folded (the union).
    pub events: usize,
    /// Events that came from `extra` and not from disk.
    pub from_extra: usize,
}

/// Parse the ticket id from a path like `tickets/<ulid>/ticket.md`.
///
/// # Errors
///
/// [`LedgerError::Invalid`] when the parent directory is not a ULID.
pub fn ticket_id_of_path(path: &str) -> Result<TicketId> {
    let dir = Path::new(path)
        .parent()
        .and_then(Path::file_name)
        .and_then(|n| n.to_str())
        .unwrap_or_default();
    dir.parse::<TicketId>().map_err(|_| {
        LedgerError::invalid(format!(
            "`{path}` is not a ticket.md inside a ULID directory"
        ))
    })
}

/// Read every `events/*.toml` of the ticket directory `ticket_dir` on disk.
///
/// # Errors
///
/// [`LedgerError::Io`] on read failures and [`LedgerError::Malformed`] on a bad file.
pub fn read_events_on_disk(ticket_dir: &Path) -> Result<Vec<Event>> {
    let dir = ticket_dir.join("events");
    let mut events = Vec::new();
    let read = match std::fs::read_dir(&dir) {
        Ok(r) => r,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(events),
        Err(e) => return Err(e.into()),
    };
    for entry in read {
        let path: PathBuf = entry?.path();
        let Some(stem) = path.file_stem().and_then(|s| s.to_str()) else {
            continue;
        };
        if path.extension().and_then(|e| e.to_str()) != Some("toml") {
            continue;
        }
        let Ok(id) = stem.parse::<EventId>() else {
            tracing::warn!(path = %path.display(), "ignoring non-ULID file in events/");
            continue;
        };
        let text = std::fs::read_to_string(&path)?;
        events.push(Event::parse(id, &text)?);
    }
    Ok(events)
}

/// Fold the union of `disk` and `extra` events of `id` into the text of `ticket.md`.
///
/// # Errors
///
/// [`LedgerError::Fold`] when the union has no valid history.
pub fn merged_document(
    id: TicketId,
    disk: Vec<Event>,
    extra: Vec<Event>,
) -> Result<(String, MergeReport)> {
    let mut events = disk;
    let mut from_extra = 0;
    for e in extra {
        if !events.iter().any(|x| x.id == e.id) {
            events.push(e);
            from_extra += 1;
        }
    }
    let folded = fold(id, &events)?;
    let text = doc::render(&folded.ticket)?;
    Ok((
        text,
        MergeReport {
            ticket: id,
            events: events.len(),
            from_extra,
        },
    ))
}

/// Resolve a conflicted `ticket.md`: write the re-folded document to `ours`.
///
/// `root` is the work tree root (git runs drivers there), `path` the
/// repo-relative path git passes as `%P`, `extra` events known from outside the
/// work tree (the other side's commit, when the caller can read it).
///
/// # Errors
///
/// [`LedgerError::Fold`] / [`LedgerError::Malformed`] when no valid history
/// exists, [`LedgerError::Io`] on filesystem failures.
pub fn resolve(root: &Path, path: &str, ours: &Path, extra: Vec<Event>) -> Result<MergeReport> {
    let id = ticket_id_of_path(path)?;
    let dir = root
        .join(path)
        .parent()
        .map_or_else(|| root.to_path_buf(), Path::to_path_buf);
    let disk = read_events_on_disk(&dir)?;
    let (text, report) = merged_document(id, disk, extra)?;
    std::fs::write(ours, text)?;
    tracing::info!(ticket = %id, events = report.events, from_extra = report.from_extra, "ticket.md re-folded by merge driver");
    Ok(report)
}
