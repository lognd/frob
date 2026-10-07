//! The ledger merge driver: union the event files, re-fold the frontmatter.
//!
//! Git invokes `frob merge-driver %O %A %B %P` for a conflicted `ticket.md`.
//! The driver never picks a side: events are append-only files, so the union
//! of every event file reachable for the ticket is the truth, and the
//! frontmatter is its fold (tickets.md section 2).
//!
//! Both layouts are served: the legacy `tickets/<ULID>/ticket.md` names its ticket in the path,
//! while a ticket-branch file at `<epic>/<slug>.md` never does, so [`locate`] reads the ULID
//! from the frontmatter of the versions git hands over (`mirror.md` section 1).

use std::path::{Path, PathBuf};

use crate::doc;
use crate::error::{LedgerError, Result};
use crate::event::Event;
use crate::fold::fold;
use crate::id::{EventId, TicketId};
use crate::layout::{self, Layout};

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

/// Which layout `path` (as git passes `%P`) belongs to and which ticket it holds.
///
/// A path inside a ULID directory is the legacy layout and names the ticket itself; any other
/// path is the ticket branch, where the id is the frontmatter ULID of the first of `versions`
/// (the texts of `%A`, `%O`, `%B`) that still shows one, conflict markers or not.
///
/// # Errors
///
/// [`LedgerError::Invalid`] when the path is not in a ULID directory and no version names a ticket.
pub fn locate(path: &str, versions: &[&str]) -> Result<(Layout, TicketId)> {
    if let Ok(id) = ticket_id_of_path(path) {
        return Ok((Layout::Dir, id));
    }
    versions
        .iter()
        .find_map(|t| layout::peek_ticket_id(t))
        .map(|id| (Layout::Branch, id))
        .ok_or_else(|| {
            LedgerError::invalid(format!(
                "`{path}` is neither in a ULID directory nor a document naming a ticket id"
            ))
        })
}

/// The directory of the event files of `id` under the work tree `root` in `layout`.
#[must_use]
pub fn events_dir_on_disk(root: &Path, path: &str, layout: Layout, id: TicketId) -> PathBuf {
    match layout {
        Layout::Dir => root
            .join(path)
            .parent()
            .map_or_else(|| root.to_path_buf(), Path::to_path_buf)
            .join("events"),
        Layout::Branch => root.join(layout::branch_events_dir(id)),
    }
}

/// Read every `events/*.toml` of the ticket directory `ticket_dir` on disk.
///
/// # Errors
///
/// [`LedgerError::Io`] on read failures and [`LedgerError::Malformed`] on a bad file.
pub fn read_events_on_disk(ticket_dir: &Path) -> Result<Vec<Event>> {
    read_events_dir(&ticket_dir.join("events"))
}

/// Read every `<ULID>.toml` event file directly inside `dir` on disk; a missing directory is empty.
///
/// # Errors
///
/// [`LedgerError::Io`] on read failures and [`LedgerError::Malformed`] on a bad file.
pub fn read_events_dir(dir: &Path) -> Result<Vec<Event>> {
    let mut events = Vec::new();
    let read = match std::fs::read_dir(dir) {
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

/// Resolve a conflicted ticket document: write the re-folded document to `ours`.
///
/// `root` is the work tree root (git runs drivers there), `path` the
/// repo-relative path git passes as `%P`, `extra` events known from outside the
/// work tree (the other side's commit, when the caller can read it). The ticket id
/// comes from the path (legacy layout) or from the document in `ours` (ticket branch).
///
/// # Errors
///
/// [`LedgerError::Fold`] / [`LedgerError::Malformed`] when no valid history
/// exists, [`LedgerError::Io`] on filesystem failures.
pub fn resolve(root: &Path, path: &str, ours: &Path, extra: Vec<Event>) -> Result<MergeReport> {
    let text = std::fs::read_to_string(ours).unwrap_or_default();
    let (layout, id) = locate(path, &[&text])?;
    resolve_at(root, path, layout, id, ours, extra)
}

/// [`resolve`] for a ticket whose layout and id the caller already [`locate`]d.
///
/// # Errors
///
/// As [`resolve`].
pub fn resolve_at(
    root: &Path,
    path: &str,
    layout: Layout,
    id: TicketId,
    ours: &Path,
    extra: Vec<Event>,
) -> Result<MergeReport> {
    let disk = read_events_dir(&events_dir_on_disk(root, path, layout, id))?;
    let (text, report) = merged_document(id, disk, extra)?;
    std::fs::write(ours, text)?;
    tracing::info!(ticket = %id, ?layout, events = report.events, from_extra = report.from_extra, "ticket document re-folded by merge driver");
    Ok(report)
}
