//! Applying a plan: staleness check, dry-run diff, atomic write, journal.

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

use crate::plan::{Edit, Plan};

/// Failure while applying a plan.
#[derive(Debug, thiserror::Error)]
pub enum FixError {
    /// A file could not be read.
    #[error("cannot read {path}: {source}")]
    Read {
        /// The file.
        path: String,
        /// Underlying error.
        source: std::io::Error,
    },
    /// A file could not be written atomically.
    #[error("cannot write {path}: {source}")]
    Write {
        /// The file.
        path: String,
        /// Underlying error.
        source: std::io::Error,
    },
}

/// Whether to write for real or only compute the diff.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    /// Compute the diff and journal; touch nothing.
    DryRun,
    /// Write every changed file atomically.
    Write,
}

/// Content hashes of the files as the check saw them.
#[derive(Debug, Clone, Default)]
pub struct Snapshot {
    digests: BTreeMap<String, blake3::Hash>,
}

impl Snapshot {
    /// An empty snapshot.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Record the bytes of `path` as the check saw them.
    pub fn record(&mut self, path: &str, bytes: &[u8]) {
        self.digests.insert(path.to_owned(), blake3::hash(bytes));
    }

    fn matches(&self, path: &str, bytes: &[u8]) -> bool {
        self.digests
            .get(path)
            .is_some_and(|d| *d == blake3::hash(bytes))
    }
}

/// What happened to one file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FileOutcome {
    /// New content computed (and written unless dry-run).
    Rewritten,
    /// The file changed since the check (or was never snapshotted); nothing written.
    Stale,
    /// The rewritten bytes failed the post-edit validator; the file keeps its pre-fix bytes.
    RolledBack {
        /// Why the validator rejected the rewrite.
        reason: String,
    },
}

/// Post-edit check run on each rewritten file: `Err(reason)` rolls the file back.
pub type Validator<'a> = &'a dyn Fn(&str, &[u8]) -> Result<(), String>;

/// The diff of one file: one hunk per edit, identical in dry-run and real runs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FileDiff {
    /// The file.
    pub path: String,
    /// Hunks rendered as ASCII text.
    pub diff: String,
}

/// One applied edit, for the fix journal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JournalEntry {
    /// Rule of the fix.
    pub rule: String,
    /// Title of the fix.
    pub title: String,
    /// The file edited.
    pub path: String,
    /// First byte replaced.
    pub start: usize,
    /// One past the last byte replaced.
    pub end: usize,
    /// Length of the replacement in bytes.
    pub new_len: usize,
}

/// Result of [`apply`].
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ApplyReport {
    /// Per-file outcomes.
    pub files: BTreeMap<String, FileOutcome>,
    /// Diffs of rewritten files.
    pub diffs: Vec<FileDiff>,
    /// One entry per applied edit.
    pub journal: Vec<JournalEntry>,
    /// Rules of fixes skipped because a file was stale or an edit was out of range.
    pub skipped: Vec<String>,
}

fn render_hunk(old: &[u8], e: &Edit) -> String {
    format!(
        "@@ {} {}..{} @@\n-{}\n+{}\n",
        e.path,
        e.start,
        e.end,
        String::from_utf8_lossy(&old[e.start..e.end]).escape_default(),
        e.replacement.escape_default(),
    )
}

/// Whether the line holding offset `start` of `old` ends in CRLF.
///
/// The edit's own line decides (the first line ending at or after `start`); an edit on an
/// unterminated last line falls back to the last ending before it, and a file with no line
/// ending at all is LF. This keeps mixed-ending files consistent line by line.
fn line_is_crlf(old: &[u8], start: usize) -> bool {
    let start = start.min(old.len());
    if let Some(i) = old[start..].iter().position(|&b| b == b'\n') {
        let nl = start + i;
        return nl > 0 && old[nl - 1] == b'\r';
    }
    match old[..start].iter().rposition(|&b| b == b'\n') {
        Some(nl) => nl > 0 && old[nl - 1] == b'\r',
        None => false,
    }
}

/// The replacement text of `e` with its line endings matched to the line it lands on.
fn replacement_for(old: &[u8], e: &Edit) -> String {
    if !e.replacement.contains('\n') || !line_is_crlf(old, e.start) {
        return e.replacement.clone();
    }
    // Normalise first so a replacement that already carries CRLF is not doubled.
    e.replacement.replace("\r\n", "\n").replace('\n', "\r\n")
}

/// Rewrite `old` with `edits`, which must be sorted by start, in range and non-overlapping.
///
/// Newlines inside a replacement take the line ending of the line they land on, so a CRLF
/// file stays CRLF; bytes outside the edited spans (BOM, trailing newline) are untouched.
pub(crate) fn splice(old: &[u8], edits: &[&Edit]) -> Vec<u8> {
    let mut new = Vec::with_capacity(old.len());
    let mut at = 0;
    for e in edits {
        new.extend_from_slice(&old[at..e.start]);
        new.extend_from_slice(replacement_for(old, e).as_bytes());
        at = e.end;
    }
    new.extend_from_slice(&old[at..]);
    new
}

fn resolve(root: &Path, rel: &str) -> PathBuf {
    root.join(rel)
}

/// Apply `plan` under `root`, refusing any file changed since `snapshot`.
///
/// # Errors
/// [`FixError`] on the first unreadable or unwritable file; earlier writes stay.
pub fn apply(
    plan: &Plan,
    root: &Path,
    snapshot: &Snapshot,
    mode: Mode,
) -> Result<ApplyReport, FixError> {
    apply_validated(plan, root, snapshot, mode, &|_, _| Ok(()))
}

/// Like [`apply`], but every rewritten file must pass `validate` (a re-parse) or it is
/// left at its pre-fix bytes and reported as [`FileOutcome::RolledBack`], never written.
///
/// # Errors
/// [`FixError`] on the first unreadable or unwritable file; earlier writes stay.
pub fn apply_validated(
    plan: &Plan,
    root: &Path,
    snapshot: &Snapshot,
    mode: Mode,
    validate: Validator<'_>,
) -> Result<ApplyReport, FixError> {
    let mut report = ApplyReport::default();
    let paths: BTreeSet<&str> = plan
        .accepted
        .iter()
        .flat_map(|f| f.edits.iter().map(|e| e.path.as_str()))
        .collect();
    let mut contents: BTreeMap<&str, Vec<u8>> = BTreeMap::new();
    for p in paths {
        let bytes = std::fs::read(resolve(root, p)).map_err(|source| FixError::Read {
            path: p.to_owned(),
            source,
        })?;
        if snapshot.matches(p, &bytes) {
            contents.insert(p, bytes);
        } else {
            tracing::warn!(path = p, "file changed since check; refusing");
            report.files.insert(p.to_owned(), FileOutcome::Stale);
        }
    }
    let mut good: Vec<&crate::plan::Fix> = Vec::new();
    for f in &plan.accepted {
        let ok = f.edits.iter().all(|e| {
            contents
                .get(e.path.as_str())
                .is_some_and(|b| e.end <= b.len())
        });
        if ok {
            good.push(f);
        } else {
            tracing::warn!(rule = %f.rule, "fix skipped: stale file or edit out of range");
            report.skipped.push(f.rule.clone());
        }
    }
    let mut by_file: BTreeMap<&str, Vec<&Edit>> = BTreeMap::new();
    for f in &good {
        for e in &f.edits {
            by_file.entry(e.path.as_str()).or_default().push(e);
            report.journal.push(JournalEntry {
                rule: f.rule.clone(),
                title: f.title.clone(),
                path: e.path.clone(),
                start: e.start,
                end: e.end,
                new_len: e.replacement.len(),
            });
        }
    }
    for (path, mut edits) in by_file {
        edits.sort_by_key(|e| (e.start, e.end));
        let old = &contents[path];
        let diff: String = edits.iter().map(|e| render_hunk(old, e)).collect();
        let new = splice(old, &edits);
        if let Err(reason) = validate(path, &new) {
            tracing::warn!(path, %reason, "rewrite failed validation; rolled back");
            report.skipped.extend(
                report
                    .journal
                    .iter()
                    .filter(|j| j.path == path)
                    .map(|j| j.rule.clone()),
            );
            report.journal.retain(|j| j.path != path);
            report
                .files
                .insert(path.to_owned(), FileOutcome::RolledBack { reason });
            continue;
        }
        if mode == Mode::Write {
            gob_fs::write_atomic(&resolve(root, path), &new).map_err(|source| FixError::Write {
                path: path.to_owned(),
                source,
            })?;
            tracing::info!(path, edits = edits.len(), "fixes written");
        }
        report.diffs.push(FileDiff {
            path: path.to_owned(),
            diff,
        });
        report.files.insert(path.to_owned(), FileOutcome::Rewritten);
    }
    Ok(report)
}
