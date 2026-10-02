//! `--fix` tier A: apply the edits of Deterministic fixes.

use std::collections::BTreeMap;
use std::path::Path;

use gob_rules::{Finding, FixKind};
use gob_text::FileInterner;

use crate::error::CheckError;
use crate::report::AppliedFix;

/// One edit resolved to a path and byte range.
struct Edit {
    start: usize,
    end: usize,
    replacement: String,
}

/// Fixes written and fixes dropped for overlapping an earlier one.
pub(crate) struct Applied {
    /// The fixes that were written.
    pub applied: Vec<AppliedFix>,
    /// Fixes skipped because an edit overlapped an accepted one.
    pub skipped_overlap: usize,
}

fn overlaps(accepted: &[(usize, usize)], start: usize, end: usize) -> bool {
    accepted
        .iter()
        .any(|&(s, e)| start < e.max(s + 1) && s < end.max(start + 1))
}

/// Apply every Deterministic fix among `findings` and write the files.
///
/// A fix is atomic: when any of its edits overlaps an edit already accepted
/// for the same file, the whole fix is skipped (the next run offers it again).
///
/// # Errors
///
/// [`CheckError::FixIo`] when a file cannot be read or written.
pub(crate) fn apply(
    root: &Path,
    findings: &[Finding],
    files: &FileInterner,
) -> Result<Applied, CheckError> {
    let mut accepted: BTreeMap<String, Vec<(usize, usize)>> = BTreeMap::new();
    let mut edits: BTreeMap<String, Vec<Edit>> = BTreeMap::new();
    let mut applied = Vec::new();
    let mut skipped_overlap = 0;
    for f in findings {
        let Some(fix) = f.fix.as_ref().filter(|x| x.kind == FixKind::Deterministic) else {
            continue;
        };
        let resolved: Option<Vec<(String, Edit)>> = fix
            .edits
            .iter()
            .map(|e| {
                files.path(e.file).map(|p| {
                    (
                        p.to_owned(),
                        Edit {
                            start: u32::from(e.range.start()) as usize,
                            end: u32::from(e.range.end()) as usize,
                            replacement: e.replacement.clone(),
                        },
                    )
                })
            })
            .collect();
        let Some(resolved) = resolved.filter(|r| !r.is_empty()) else {
            tracing::warn!(rule = %f.rule, "fix names an unknown file; skipped");
            continue;
        };
        if resolved
            .iter()
            .any(|(p, e)| accepted.get(p).is_some_and(|a| overlaps(a, e.start, e.end)))
        {
            tracing::info!(rule = %f.rule, title = %fix.title, "fix overlaps an accepted fix; skipped");
            skipped_overlap += 1;
            continue;
        }
        let first = resolved[0].0.clone();
        for (path, e) in resolved {
            accepted
                .entry(path.clone())
                .or_default()
                .push((e.start, e.end));
            edits.entry(path).or_default().push(e);
        }
        applied.push(AppliedFix {
            rule: f.rule.to_string(),
            file: first,
            title: fix.title.clone(),
        });
    }
    for (path, mut list) in edits {
        let full = root.join(&path);
        let mut text = std::fs::read_to_string(&full)
            .map_err(|e| CheckError::FixIo(format!("read {path}: {e}")))?;
        list.sort_by_key(|e| std::cmp::Reverse(e.start));
        for e in &list {
            if e.end > text.len()
                || e.start > e.end
                || !text.is_char_boundary(e.start)
                || !text.is_char_boundary(e.end)
            {
                tracing::warn!(
                    path,
                    start = e.start,
                    end = e.end,
                    "edit out of range; skipped"
                );
                continue;
            }
            text.replace_range(e.start..e.end, &e.replacement);
        }
        std::fs::write(&full, text).map_err(|e| CheckError::FixIo(format!("write {path}: {e}")))?;
        tracing::info!(path, edits = list.len(), "fix written");
    }
    applied.sort_by(|a, b| (&a.file, &a.rule).cmp(&(&b.file, &b.rule)));
    Ok(Applied {
        applied,
        skipped_overlap,
    })
}
