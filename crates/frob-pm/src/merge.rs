//! Merge of a conflicted object frontmatter: union the event files, re-fold.
//!
//! Two branches that edited one milestone each added event files and rewrote
//! the frontmatter; git conflicts only on the frontmatter. Events are
//! append-only files, so the union on disk is the truth and the frontmatter is
//! its fold. [`resolve`] is the pm counterpart of the ticket merge driver; the CLI
//! crate dispatches `frob merge-driver` to it. Git may run the driver before the
//! other side's event files are checked out, so [`resolve_with`] also takes events
//! read from the merged commits.

use std::collections::BTreeSet;
use std::path::Path;

use frob_ledger::EventId;

use crate::error::{PmError, Result};
use crate::event::PmEvent;
use crate::fold::fold;
use crate::model::{ObjectId, ObjectKind};

/// What a merge resolved.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MergeReport {
    /// The object.
    pub id: ObjectId,
    /// Events folded (the union).
    pub events: usize,
    /// Events that were not on disk and came from the extra (history) set.
    pub from_extra: usize,
}

/// Kind and id of a path like `tickets/_milestones/<ulid>/milestone.md`.
///
/// # Errors
///
/// [`PmError::Invalid`] when the path is not an object frontmatter file.
pub fn object_of_path(path: &str) -> Result<(ObjectKind, ObjectId)> {
    let p = Path::new(path);
    let file = p.file_name().and_then(|n| n.to_str()).unwrap_or_default();
    let dir = p
        .parent()
        .and_then(Path::file_name)
        .and_then(|n| n.to_str())
        .unwrap_or_default();
    ObjectKind::ALL
        .into_iter()
        .find(|k| k.file() == file)
        .and_then(|k| dir.parse().ok().map(|id| (k, id)))
        .ok_or_else(|| {
            PmError::invalid(format!(
                "`{path}` is not a milestone or cycle file in a ULID directory"
            ))
        })
}

/// Read every `events/*.toml` of the object directory `dir` on disk.
///
/// # Errors
///
/// [`PmError::Malformed`] on a read failure or bad file.
pub fn read_events_on_disk(dir: &Path) -> Result<Vec<PmEvent>> {
    let events_dir = dir.join("events");
    let read = match std::fs::read_dir(&events_dir) {
        Ok(r) => r,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
        Err(e) => {
            return Err(PmError::malformed(
                events_dir.display().to_string(),
                e.to_string(),
            ));
        }
    };
    let mut events = Vec::new();
    for entry in read {
        let path = entry
            .map_err(|e| PmError::malformed(events_dir.display().to_string(), e.to_string()))?
            .path();
        let Some(id) = path
            .file_stem()
            .and_then(|s| s.to_str())
            .and_then(|s| s.parse::<EventId>().ok())
        else {
            continue;
        };
        if path.extension().and_then(|e| e.to_str()) != Some("toml") {
            continue;
        }
        let text = std::fs::read_to_string(&path)
            .map_err(|e| PmError::malformed(path.display().to_string(), e.to_string()))?;
        events.push(PmEvent::parse(id, &text)?);
    }
    Ok(events)
}

/// Resolve a conflicted frontmatter from the events on disk: write the re-folded file to `ours`.
///
/// # Errors
///
/// As [`resolve_with`].
pub fn resolve(root: &Path, path: &str, ours: &Path) -> Result<MergeReport> {
    resolve_with(root, path, ours, Vec::new())
}

/// Resolve a conflicted frontmatter: union the events on disk with `extra`, re-fold, write to `ours`.
///
/// `root` is the work tree root, `path` the repo-relative path git passes as `%P`;
/// `extra` holds events read from the merged commits (duplicates by id are dropped).
///
/// # Errors
///
/// [`PmError::Invalid`] for a foreign path, [`PmError::Fold`] / [`PmError::Malformed`]
/// when no valid history exists, [`PmError::Malformed`] when `ours` cannot be written.
pub fn resolve_with(
    root: &Path,
    path: &str,
    ours: &Path,
    extra: Vec<PmEvent>,
) -> Result<MergeReport> {
    let (kind, id) = object_of_path(path)?;
    let dir = root
        .join(path)
        .parent()
        .map_or_else(|| root.to_path_buf(), Path::to_path_buf);
    let mut events = read_events_on_disk(&dir)?;
    let on_disk = events.len();
    let mut seen: BTreeSet<EventId> = events.iter().map(|e| e.id).collect();
    for ev in extra {
        if seen.insert(ev.id) {
            events.push(ev);
        }
    }
    let from_extra = events.len() - on_disk;
    let folded = fold(kind, id, &events)?;
    std::fs::write(ours, folded.object.render()?)
        .map_err(|e| PmError::malformed(ours.display().to_string(), e.to_string()))?;
    tracing::info!(object = %id, events = events.len(), from_extra, "frontmatter re-folded by pm merge");
    Ok(MergeReport {
        id,
        events: events.len(),
        from_extra,
    })
}
