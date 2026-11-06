//! `grimble shrink`: turn the CAP002 findings of a binding into reviewable grant removals.
//!
//! A CAP002 finding (Warn) is only fired when absence is Exact (binding.md 7.2 item 6), which is
//! the one case shrink acts on. The plan is pure: it reads model text through a callback and
//! returns the edited text and a diff; the caller decides whether to write it (dry run by default).
//!
//! Besides removals, shrink proposes `owns` selectors from ownership: each directory SYS001 reports
//! as unowned gets an `owns "<dir>/**";` clause added to the node whose existing `owns` selectors
//! share the longest directory prefix with it (a directory no node is near is skipped, never
//! guessed).
//!
//! Known limits: only `may` grants are removed (an interactive excuse prompt is not implemented;
//! each removal instead carries the `excuses` clause to write if the grant is deliberately kept).

// frob:ticket 01M3Z714HJ6E02VGXH271BAAE0
// frob:ticket 01M5A7E4S1CQJ834X4409EPWW0

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::Path;

use grimble_model::ast::EntityKind;

use crate::model::Model;
use crate::types::BindFinding;
use crate::types::Role;

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

/// Where a node's `owns` clauses sit, so a new selector can be written beside them.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OwnsSite {
    /// The node name (the anchor without its `node/` prefix).
    pub node: String,
    /// Repo-relative `.grmb` file of the last `owns` clause.
    pub file: String,
    /// Byte offset one past the last `owns` clause.
    pub end: usize,
    /// Every `owns` selector text of the node.
    pub selectors: Vec<String>,
}

/// One `owns` selector proposed for addition to a node.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OwnsAddition {
    /// Repo-relative `.grmb` file the clause is written into.
    pub file: String,
    /// The node that gains the selector.
    pub node: String,
    /// The `owns` clause to write.
    pub clause: String,
    /// The unowned directory the selector covers.
    pub dir: String,
    /// 1-based line the clause is inserted at.
    pub line: usize,
}

/// The planned edits: removals, additions, the files they touch and their edited text.
#[derive(Clone, Debug, Default)]
pub struct Plan {
    /// Every proposed removal, ordered by file then position.
    pub removals: Vec<Removal>,
    /// Every proposed `owns` addition, ordered by file then position.
    pub additions: Vec<OwnsAddition>,
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

/// The `owns` sites of every node with an `owns` clause in `model`.
#[must_use]
pub fn owns_sites(model: &Model) -> Vec<OwnsSite> {
    let mut out = Vec::new();
    for e in model
        .entities
        .values()
        .filter(|e| e.kind == EntityKind::Node)
    {
        let Some(last) = e.clauses_of(Role::Owns).last() else {
            continue;
        };
        out.push(OwnsSite {
            node: e
                .anchor
                .strip_prefix("node/")
                .unwrap_or(&e.anchor)
                .to_owned(),
            file: last.file.clone(),
            end: last.span.end,
            selectors: e
                .clauses_of(Role::Owns)
                .filter_map(|c| c.selector_text.clone())
                .collect(),
        });
    }
    out
}

/// Leading literal directory components of a selector text (`"src/a/**"` gives `src`, `a`).
fn literal_dirs(selector: &str) -> Vec<&str> {
    let t = selector.trim().trim_matches('"');
    let mut parts: Vec<&str> = t.split('/').collect();
    parts.pop();
    parts
        .into_iter()
        .take_while(|p| !p.is_empty() && !p.contains(['*', '?', '[', '{']))
        .collect()
}

/// How many leading directory components `dir` shares with the best selector of `site`.
fn nearness(site: &OwnsSite, dir: &str) -> usize {
    let want: Vec<&str> = dir.split('/').collect();
    site.selectors
        .iter()
        .map(|s| {
            literal_dirs(s)
                .iter()
                .zip(&want)
                .take_while(|(a, b)| a == b)
                .count()
        })
        .max()
        .unwrap_or(0)
}

/// The node site nearest to `dir`, `None` when no node shares a leading directory with it.
fn nearest_site<'a>(sites: &'a [OwnsSite], dir: &str) -> Option<&'a OwnsSite> {
    sites
        .iter()
        .map(|s| (nearness(s, dir), s))
        .filter(|(n, _)| *n > 0)
        .max_by(|a, b| a.0.cmp(&b.0).then_with(|| b.1.node.cmp(&a.1.node)))
        .map(|(_, s)| s)
}

/// The text of the line holding byte `at`, its start offset and its leading whitespace.
fn line_start_after(text: &str, at: usize) -> (usize, String) {
    let at = at.min(text.len());
    let ls = text[..at].rfind('\n').map_or(0, |i| i + 1);
    let indent: String = text[ls..]
        .chars()
        .take_while(|c| *c == ' ' || *c == '\t')
        .collect();
    let next = text[at..].find('\n').map_or(text.len(), |i| at + i + 1);
    (next, indent)
}

/// Plan the removal of every declared-unused grant among `findings`; `read` yields a file's text.
pub fn plan(findings: &[BindFinding], read: &mut dyn FnMut(&str) -> Option<String>) -> Plan {
    plan_with_owns(findings, &[], read)
}

/// [`plan`] plus `owns` additions for each SYS001 unowned directory, written beside `sites`.
pub fn plan_with_owns(
    findings: &[BindFinding],
    sites: &[OwnsSite],
    read: &mut dyn FnMut(&str) -> Option<String>,
) -> Plan {
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
    let mut inserts: BTreeMap<String, Vec<(usize, String, String)>> = BTreeMap::new();
    let mut seen = std::collections::BTreeSet::new();
    for f in findings
        .iter()
        .filter(|f| f.rule == "SYS001" && f.reason.is_none() && f.file.is_none())
    {
        let dir = f.anchor.as_str();
        if dir == "." || !seen.insert(dir.to_owned()) {
            continue;
        }
        let Some(site) = nearest_site(sites, dir) else {
            tracing::warn!(%dir, "no node is near the unowned directory; owns not proposed");
            out.skipped.push(format!("{dir}: no nearby node to own it"));
            continue;
        };
        if !texts.contains_key(&site.file) {
            let Some(t) = read(&site.file) else {
                tracing::warn!(file = %site.file, "shrink cannot read the model file; owns skipped");
                out.skipped.push(format!("{}: unreadable", site.file));
                continue;
            };
            texts.insert(site.file.clone(), t);
        }
        let text = &texts[&site.file];
        let (pos, indent) = line_start_after(text, site.end);
        let clause = format!("owns \"{dir}/**\";");
        tracing::info!(file = %site.file, node = %site.node, %dir, "owns proposed");
        out.additions.push(OwnsAddition {
            file: site.file.clone(),
            node: site.node.clone(),
            clause: clause.clone(),
            dir: dir.to_owned(),
            line: line_of(text, pos.saturating_sub(1)) + 1,
        });
        inserts.entry(site.file.clone()).or_default().push((
            pos,
            format!("{indent}{clause}\n"),
            clause,
        ));
    }
    out.additions
        .sort_by(|a, b| (&a.file, a.line, &a.dir).cmp(&(&b.file, b.line, &b.dir)));
    let files: std::collections::BTreeSet<String> =
        ranges.keys().chain(inserts.keys()).cloned().collect();
    for file in files {
        let old = &texts[&file];
        let mut rs = ranges.remove(&file).unwrap_or_default();
        rs.sort_unstable();
        rs.dedup();
        let mut ins = inserts.remove(&file).unwrap_or_default();
        ins.sort_by_key(|i| i.0);
        // Edits as (start, end, replacement) over the old text, applied back to front.
        let mut edits: Vec<(usize, usize, String)> = Vec::new();
        for r in &rs {
            let (a, b) = widen(old, *r);
            edits.push((a, b, String::new()));
        }
        for (pos, text, _) in &ins {
            edits.push((*pos, *pos, text.clone()));
        }
        edits.sort_by(|x, y| (y.0, y.1).cmp(&(x.0, x.1)));
        let mut new = old.clone();
        for (a, b, rep) in &edits {
            new.replace_range(*a..*b, rep);
        }
        writeln!(out.diff, "--- a/{file}\n+++ b/{file}").ok();
        for r in &rs {
            let (a, b) = widen(old, *r);
            let line = line_of(old, a);
            writeln!(out.diff, "@@ line {line} @@").ok();
            for l in old[a..b].lines() {
                writeln!(out.diff, "-{l}").ok();
            }
            let rest = format!("{}{}", &old[a..r.0], &old[r.1..b]);
            if !rest.trim().is_empty() {
                writeln!(out.diff, "+{}", rest.trim_end()).ok();
            }
        }
        for (pos, text, _) in &ins {
            writeln!(out.diff, "@@ line {} @@", line_of(old, *pos)).ok();
            for l in text.lines() {
                writeln!(out.diff, "+{l}").ok();
            }
        }
        out.edited.insert(file, new);
    }
    tracing::info!(
        removals = out.removals.len(),
        additions = out.additions.len(),
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
