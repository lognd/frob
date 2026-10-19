//! `grimble shrink`: turn the CAP002 findings of a binding into reviewable grant removals.
//!
//! A CAP002 finding (Warn) is only fired when absence is Exact (binding.md 7.2 item 6), which is
//! the one case shrink acts on. The plan is pure: it reads model text through a callback and
//! returns the edited text and a diff; the caller decides whether to write it (dry run by default).
//!
//! Known limits: only `may` grants are removed (owns selector proposals and an interactive excuse
//! prompt are not implemented; each removal instead carries the `excuses` clause to write if the
//! grant is deliberately kept).

// frob:ticket 01M3Z714HJ6E02VGXH271BAAE0

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::Path;

use crate::types::BindFinding;

/// The rule whose resolved findings shrink acts on.
pub const SHRINK_RULE: &str = "CAP002";

/// One grant clause proposed for removal.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Removal {
    /// Repo-relative `.grmb` file.
    pub file: String,
    /// The node the grant belongs to.
    pub node: String,
    /// The grant clause text as written.
    pub clause: String,
    /// 1-based line the clause starts on.
    pub line: usize,
    /// Byte range of the clause in the file.
    pub range: (usize, usize),
    /// The clause to write instead to keep the grant with a stated reason.
    pub excuse_hint: String,
}

/// The planned edits: removals, the files they touch and their edited text.
#[derive(Clone, Debug, Default)]
pub struct Plan {
    /// Every proposed removal, ordered by file then position.
    pub removals: Vec<Removal>,
    /// Edited text per file.
    pub edited: BTreeMap<String, String>,
    /// A unified-style diff of all edits; empty when nothing is proposed.
    pub diff: String,
    /// Findings skipped because their file could not be read or the range was not a clause.
    pub skipped: Vec<String>,
}

/// The node anchor and atom out of a CAP002 anchor (`cap/node/<name>/<atom>`).
fn split_anchor(anchor: &str) -> (String, String) {
    let rest = anchor.strip_prefix("cap/").unwrap_or(anchor);
    match rest.rsplit_once('/') {
        Some((node, atom)) => (node.to_owned(), atom.to_owned()),
        None => (rest.to_owned(), String::new()),
    }
}

/// 1-based line of byte `at` in `text`.
fn line_of(text: &str, at: usize) -> usize {
    text[..at].bytes().filter(|b| *b == b'\n').count() + 1
}

/// Widen `range` to its whole lines when only whitespace shares them, so no blank line is left.
fn widen(text: &str, range: (usize, usize)) -> (usize, usize) {
    let start = text[..range.0].rfind('\n').map_or(0, |i| i + 1);
    let end = text[range.1..]
        .find('\n')
        .map_or(text.len(), |i| range.1 + i + 1);
    let before_blank = text[start..range.0].trim().is_empty();
    let after_blank = text[range.1..end].trim().is_empty();
    if before_blank && after_blank {
        (start, end)
    } else {
        range
    }
}

/// Plan the removal of every declared-unused grant among `findings`; `read` yields a file's text.
pub fn plan(findings: &[BindFinding], read: &mut dyn FnMut(&str) -> Option<String>) -> Plan {
    let mut texts: BTreeMap<String, String> = BTreeMap::new();
    let mut out = Plan::default();
    let mut ranges: BTreeMap<String, Vec<(usize, usize)>> = BTreeMap::new();
    for f in findings
        .iter()
        .filter(|f| f.rule == SHRINK_RULE && f.reason.is_none())
    {
        let (Some(file), Some(range)) = (f.file.as_ref(), f.range) else {
            continue;
        };
        if !texts.contains_key(file) {
            let Some(t) = read(file) else {
                tracing::warn!(%file, "shrink cannot read the model file; grant skipped");
                out.skipped.push(format!("{file}: unreadable"));
                continue;
            };
            texts.insert(file.clone(), t);
        }
        let text = &texts[file];
        let Some(clause) = text
            .get(range.0..range.1)
            .filter(|c| c.trim_start().starts_with("may"))
        else {
            tracing::warn!(%file, ?range, "shrink range is not a may clause; grant skipped");
            out.skipped
                .push(format!("{file}: not a may clause at {range:?}"));
            continue;
        };
        let (node, atom) = split_anchor(&f.anchor);
        tracing::info!(%file, %node, %atom, "grant proposed for removal");
        out.removals.push(Removal {
            file: file.clone(),
            node,
            clause: clause.trim().to_owned(),
            line: line_of(text, range.0),
            range,
            excuse_hint: format!("excuses {atom} because=\"<why the grant stays>\";"),
        });
        ranges.entry(file.clone()).or_default().push(range);
    }
    out.removals
        .sort_by(|a, b| (&a.file, a.range.0).cmp(&(&b.file, b.range.0)));
    for (file, mut rs) in ranges {
        let old = &texts[&file];
        rs.sort_unstable();
        rs.dedup();
        let mut new = old.clone();
        for r in rs.iter().rev() {
            let (a, b) = widen(old, *r);
            new.replace_range(a..b, "");
        }
        let _ = writeln!(out.diff, "--- a/{file}\n+++ b/{file}");
        for r in &rs {
            let (a, b) = widen(old, *r);
            let line = line_of(old, a);
            let _ = writeln!(out.diff, "@@ line {line} @@");
            for l in old[a..b].lines() {
                let _ = writeln!(out.diff, "-{l}");
            }
            let rest = format!("{}{}", &old[a..r.0], &old[r.1..b]);
            if !rest.trim().is_empty() {
                let _ = writeln!(out.diff, "+{}", rest.trim_end());
            }
        }
        out.edited.insert(file, new);
    }
    tracing::info!(
        removals = out.removals.len(),
        files = out.edited.len(),
        "shrink planned"
    );
    out
}

/// A failure writing the shrunk model files.
#[derive(Debug, thiserror::Error)]
pub enum ShrinkError {
    /// A model file could not be written.
    #[error("cannot write {file}: {source}")]
    Write {
        /// Repo-relative file.
        file: String,
        /// The io failure.
        source: std::io::Error,
    },
}

impl Plan {
    /// Write every edited file under `root`; the only mutating step, never reached on a dry run.
    ///
    /// # Errors
    ///
    /// [`ShrinkError::Write`] for the first file that cannot be written.
    pub fn apply(&self, root: &Path) -> Result<(), ShrinkError> {
        for (file, text) in &self.edited {
            std::fs::write(root.join(file), text).map_err(|source| ShrinkError::Write {
                file: file.clone(),
                source,
            })?;
            tracing::info!(%file, "shrunk model written");
        }
        Ok(())
    }
}
