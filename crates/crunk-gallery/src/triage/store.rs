//! Manifest persistence for triage: load, merge a render run, set verdicts, save as v3.

// frob:ticket 01M43ATE06MNRNVJJ314KW24RJ

use std::path::Path;

use gob_time::Day;
use serde_json::{Value, json};

use super::TriageError;
use crate::cells::Cell;
use crate::manifest::{self, Entry, Manifest, Render, Status, Verdict};
use crate::render::Rendered;

/// The wire name of `status` in a manifest.
pub const fn status_name(status: Status) -> &'static str {
    match status {
        Status::Pending => "pending",
        Status::Approved => "approved",
        Status::Rejected => "rejected",
    }
}

/// The status a wire name stands for, or `None` for an unknown name.
pub fn parse_status(name: &str) -> Option<Status> {
    match name {
        "pending" => Some(Status::Pending),
        "approved" => Some(Status::Approved),
        "rejected" => Some(Status::Rejected),
        _ => None,
    }
}

/// An empty v3 manifest.
pub const fn empty() -> Manifest {
    Manifest {
        version: 3,
        entries: Vec::new(),
    }
}

/// Read the manifest at `path`; a missing file is an empty manifest.
///
/// # Errors
///
/// [`TriageError::Io`] when the file exists but cannot be read, [`TriageError::Manifest`] when it
/// does not parse.
pub fn load_or_empty(path: &Path) -> Result<Manifest, TriageError> {
    match std::fs::read_to_string(path) {
        Ok(text) => Ok(manifest::parse(&text)?),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            tracing::debug!(path = ?path, "no manifest yet; starting empty");
            Ok(empty())
        }
        Err(e) => Err(e.into()),
    }
}

/// The v3 JSON document for `manifest`; v1 rows with no state (wildcards) cannot be written and
/// are dropped, so call [`expand_wildcards`] first.
pub fn to_value(manifest: &Manifest) -> Value {
    let cells: Vec<Value> = manifest
        .entries
        .iter()
        .filter_map(|e| {
            let state = e.state.as_deref()?;
            let mut row = json!({"screen": e.screen, "state": state, "platform": e.platform});
            if let Some(r) = e.render.as_ref().filter(|r| r.sha256.is_some()) {
                row["render"] = json!({"path": r.path, "sha256": r.sha256});
            }
            if let Some(v) = &e.verdict {
                let mut d = json!({"status": status_name(v.status)});
                for (key, val) in [
                    ("reviewer", &v.reviewer),
                    ("reviewed_at", &v.reviewed_at),
                    ("expires_at", &v.expires_at),
                ] {
                    if let Some(val) = val {
                        d[key] = json!(val);
                    }
                }
                row["verdict"] = d;
            }
            Some(row)
        })
        .collect();
    json!({"version": 3, "cells": cells})
}

/// Write `manifest` to `path` atomically as a v3 document.
///
/// # Errors
///
/// [`TriageError::Io`] when the write fails.
pub fn save(path: &Path, manifest: &Manifest) -> Result<(), TriageError> {
    let mut text = serde_json::to_string_pretty(&to_value(manifest))
        .map_err(|e| TriageError::Invalid(e.to_string()))?;
    text.push('\n');
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir)?;
    }
    gob_fs::write_atomic(path, text.as_bytes())?;
    tracing::info!(path = ?path, entries = manifest.entries.len(), "gallery manifest saved");
    Ok(())
}

/// Replace each state-less (v1) row by one exact row per cell it covers.
pub fn expand_wildcards(manifest: &mut Manifest, cells: &[Cell]) {
    let wild: Vec<Entry> = manifest
        .entries
        .iter()
        .filter(|e| e.state.is_none())
        .cloned()
        .collect();
    manifest.entries.retain(|e| e.state.is_some());
    for w in wild {
        for c in cells
            .iter()
            .filter(|c| c.screen == w.screen && c.platform == w.platform)
        {
            if position(manifest, c).is_none() {
                manifest.entries.push(Entry {
                    state: Some(c.state.clone()),
                    ..w.clone()
                });
            }
        }
    }
    manifest.version = 3;
}

fn position(manifest: &Manifest, cell: &Cell) -> Option<usize> {
    manifest.entries.iter().position(|e| {
        e.screen == cell.screen
            && e.platform == cell.platform
            && e.state.as_deref() == Some(cell.state.as_str())
    })
}

fn entry_mut<'a>(manifest: &'a mut Manifest, cell: &Cell) -> &'a mut Entry {
    let at = position(manifest, cell).unwrap_or_else(|| {
        manifest.entries.push(Entry {
            screen: cell.screen.clone(),
            state: Some(cell.state.clone()),
            platform: cell.platform.clone(),
            render: None,
            verdict: None,
        });
        manifest.entries.len() - 1
    });
    &mut manifest.entries[at]
}

/// Record a fresh render of `cell`: a changed image invalidates the verdict (it judged other pixels).
pub fn apply_render(manifest: &mut Manifest, cell: &Cell, rendered: &Rendered) {
    let entry = entry_mut(manifest, cell);
    let same = entry
        .render
        .as_ref()
        .is_some_and(|r| r.sha256.as_deref() == Some(rendered.sha256.as_str()));
    if !same && entry.verdict.take().is_some() {
        tracing::info!(screen = %cell.screen, state = %cell.state, platform = %cell.platform, "render changed; verdict cleared");
    }
    entry.render = Some(Render {
        path: rendered.path.clone(),
        sha256: Some(rendered.sha256.clone()),
    });
}

/// Who decides, when, and how long an approval lasts.
#[derive(Debug, Clone)]
pub struct Reviewer {
    /// Reviewer name written into the verdict.
    pub name: String,
    /// The day of the decision.
    pub today: Day,
    /// Days an approval stays valid; `None` never expires.
    pub expires_in_days: Option<i64>,
}

/// Set the verdict of `cell` to `status`, attributed to `by`.
///
/// # Errors
///
/// [`TriageError::Invalid`] when the cell has no render yet or the expiry date is out of range.
pub fn set_verdict(
    manifest: &mut Manifest,
    cell: &Cell,
    status: Status,
    by: &Reviewer,
) -> Result<(), TriageError> {
    let entry = entry_mut(manifest, cell);
    if entry.render.is_none() {
        return Err(TriageError::Invalid(format!(
            "{}/{} on {} has no render to judge",
            cell.screen, cell.state, cell.platform
        )));
    }
    let expires_at = match (status, by.expires_in_days) {
        (Status::Approved, Some(days)) => Some(
            by.today
                .plus_days(days)
                .map_err(TriageError::Invalid)?
                .to_string(),
        ),
        _ => None,
    };
    entry.verdict = Some(Verdict {
        status,
        reviewer: Some(by.name.clone()),
        reviewed_at: Some(by.today.to_string()),
        expires_at,
    });
    tracing::info!(screen = %cell.screen, state = %cell.state, platform = %cell.platform, status = status_name(status), "verdict recorded");
    Ok(())
}
