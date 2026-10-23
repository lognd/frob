//! Validating the map against the repository at HEAD and planning every file edit.

// frob:ticket 01M4H0WXVXJ18DX9SVX6EHT0AD

use std::path::Path;

use gob_git::Repo;
use gob_text::{Headings, Locator};

use crate::moved::{MOVED_PATH, MovedError, MovedMap};
use crate::rewrite::{in_scope, remap_text};

/// A map row whose target does not exist at HEAD.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RowProblem {
    /// The row key.
    pub key: String,
    /// The row value as written.
    pub value: String,
    /// What is wrong with the target.
    pub reason: String,
}

/// Why a remap could not be planned.
#[derive(Debug, thiserror::Error)]
pub enum RemapError {
    /// Rows whose targets are not headings of the new file at HEAD; nothing is written.
    #[error("{} map row(s) point at places that do not exist at HEAD", .0.len())]
    Refused(Vec<RowProblem>),
    /// `docs/MOVED.toml` is absent.
    #[error("{MOVED_PATH} does not exist")]
    NoMap,
    /// The map does not parse or a row never settles.
    #[error(transparent)]
    Moved(#[from] MovedError),
    /// Reading the repository failed.
    #[error("git: {0}")]
    Git(String),
    /// Reading a work-tree file failed.
    #[error("io: {0}")]
    Io(String),
}

/// The new text of one file.
#[derive(Debug, Clone)]
pub struct FileChange {
    /// Repo-relative path.
    pub path: String,
    /// The rewritten content.
    pub new_text: String,
}

/// The validated rewrite: the row count and every changed file.
#[derive(Debug, Clone, Default)]
pub struct Plan {
    /// Rows in the map.
    pub rows: usize,
    /// Files whose text changes, in path order.
    pub changes: Vec<FileChange>,
}

/// The row problems of `map` against HEAD: targets that are missing or offer no such heading, and cycles.
fn check_rows(repo: &Repo, map: &MovedMap) -> Result<Vec<RowProblem>, RemapError> {
    let mut problems = Vec::new();
    for row in map.rows() {
        let problem = |reason: String| RowProblem {
            key: row.key.clone(),
            value: row.value.clone(),
            reason,
        };
        if let Err(e) = map.resolve(&row.from.file, row.from.locator.as_ref(), true) {
            problems.push(problem(e.to_string()));
            continue;
        }
        let Some(to) = row.to.as_ref().filter(|_| row.moves()) else {
            continue;
        };
        let blob = repo
            .read_blob_at("HEAD", to.file.trim_start_matches("./"))
            .map_err(|e| RemapError::Git(e.to_string()))?;
        let Some(blob) = blob else {
            problems.push(problem(format!("`{}` does not exist at HEAD", to.file)));
            continue;
        };
        if let Some(loc) = &to.locator {
            let heads = Headings::parse(&String::from_utf8_lossy(&blob));
            if !heads.offers(loc) {
                let what = match loc {
                    Locator::Anchor(a) => format!("anchor `#{a}`"),
                    Locator::Section(n) => format!("section {n}"),
                };
                problems.push(problem(format!(
                    "{what} is not a heading of `{}` at HEAD",
                    to.file
                )));
            }
        }
    }
    Ok(problems)
}

/// Validate `map` against HEAD of `repo`, then plan the rewrite of every in-scope tracked file under `root`.
///
/// # Errors
/// [`RemapError::Refused`] naming each bad row (nothing is planned), or a read or cycle error.
pub fn remap(repo: &Repo, root: &Path, map: &MovedMap) -> Result<Plan, RemapError> {
    let problems = check_rows(repo, map)?;
    if !problems.is_empty() {
        tracing::warn!(rows = problems.len(), "map refused");
        return Err(RemapError::Refused(problems));
    }
    let mut paths: Vec<String> = repo
        .blobs_at("HEAD")
        .map_err(|e| RemapError::Git(e.to_string()))?
        .into_iter()
        .map(|(p, _)| p)
        .filter(|p| in_scope(p))
        .collect();
    paths.sort();
    let mut changes = Vec::new();
    for path in paths {
        let Ok(text) = std::fs::read_to_string(root.join(&path)) else {
            continue;
        };
        if let Some(new_text) = remap_text(&path, &text, map)? {
            changes.push(FileChange { path, new_text });
        }
    }
    tracing::info!(
        rows = map.rows().len(),
        files = changes.len(),
        "remap planned"
    );
    Ok(Plan {
        rows: map.rows().len(),
        changes,
    })
}
