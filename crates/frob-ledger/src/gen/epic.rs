//! `<epic>/README.md`: one page per top epic, its tickets grouped by sub-epic and then by status
//! (`navigation.md` section 3.1).
//!
//! Every ticket that is not `_unfiled` appears on exactly one epic page and, on it, in exactly one
//! status section. Pages are not row-capped, because the cross-check ([`check`], rule `GEN001`)
//! relies on that exactly-one property. The output is a pure function of the tree.
// frob:ticket 01M3ZX860YGPCJE6ETPJADMNFE

use std::collections::BTreeMap;
use std::fmt::Write as _;

use crate::layout::{EPIC_FILE, UNFILED_DIR};
use crate::model::{Category, TicketType};
use crate::reindex::GenInput;

use super::indexes::{Row, cell, header, load, ranked};

/// File name of an epic page inside its directory.
pub const PAGE: &str = "README.md";

/// Rule id reported by [`check`].
pub const GEN001: &str = "GEN001";

/// A ticket that the epic pages do not list exactly once (rule `GEN001`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CoverageDrift {
    /// The ticket at `path` is listed on no epic page.
    Missing {
        /// Branch-relative path of the ticket.
        path: String,
    },
    /// The ticket at `path` is listed `count` times (more than once).
    Duplicate {
        /// Branch-relative path of the ticket.
        path: String,
        /// How many rows list it.
        count: usize,
    },
}

impl CoverageDrift {
    /// The rule id, always `GEN001`.
    #[must_use]
    pub const fn rule(&self) -> &'static str {
        GEN001
    }
}

impl std::fmt::Display for CoverageDrift {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Missing { path } => {
                write!(f, "{GEN001}: ticket `{path}` is on no epic page")
            }
            Self::Duplicate { path, count } => {
                write!(
                    f,
                    "{GEN001}: ticket `{path}` is listed {count} times on the epic pages"
                )
            }
        }
    }
}

/// The directory (first path segment) of a ticket path, if it has one.
pub(super) fn dir_of(path: &str) -> Option<&str> {
    path.split_once('/').map(|(d, _)| d)
}

/// The link target of `path` as written on the page that lists it: relative to `dir` when given.
fn target(path: &str, dir: Option<&str>) -> String {
    let rel = dir
        .and_then(|d| path.strip_prefix(d).and_then(|r| r.strip_prefix('/')))
        .unwrap_or(path);
    rel.replace(' ', "%20")
}

/// One ticket row of a status table; links are relative to `dir` when given.
fn row_line(r: &Row, dir: Option<&str>) -> String {
    format!(
        "| {} | {} | {} | {} | [{}]({}) |\n",
        r.handle,
        cell(&r.front.title),
        r.front.priority,
        r.front
            .points
            .map_or_else(|| "-".to_owned(), |p| p.get().to_string()),
        cell(&r.path),
        target(&r.path, dir),
    )
}

/// One `### status (n)` table per non-empty category of `rows`, in category order.
pub(super) fn status_sections(rows: &[&Row], dir: Option<&str>, level: &str) -> String {
    let mut out = String::new();
    for c in Category::ALL {
        let mut in_c: Vec<&Row> = rows
            .iter()
            .copied()
            .filter(|r| r.front.category == *c)
            .collect();
        if in_c.is_empty() {
            continue;
        }
        in_c.sort_by_key(|r| ranked(r));
        let _ = write!(
            out,
            "{level} {} ({})\n\n| Handle | Title | Priority | Points | Path |\n|---|---|---|---|---|\n",
            c.as_str(),
            in_c.len()
        );
        for r in in_c {
            out.push_str(&row_line(r, dir));
        }
        out.push('\n');
    }
    out
}

/// Tickets of each top-epic directory, keyed by directory (never `_unfiled`).
pub(super) fn by_dir(rows: &[Row]) -> BTreeMap<&str, Vec<&Row>> {
    let mut dirs: BTreeMap<&str, Vec<&Row>> = BTreeMap::new();
    for r in rows {
        if let Some(d) = dir_of(&r.path).filter(|d| *d != UNFILED_DIR) {
            dirs.entry(d).or_default().push(r);
        }
    }
    dirs
}

/// The top epic of a directory and its display title.
pub(super) fn top_of<'a>(dir: &str, rows: &[&'a Row]) -> Option<&'a Row> {
    let epic_path = format!("{dir}/{EPIC_FILE}");
    rows.iter().copied().find(|r| r.path == epic_path)
}

/// Render one `<epic>/README.md` per top-epic directory.
#[must_use]
pub fn render(input: &GenInput<'_>) -> Vec<(String, Vec<u8>)> {
    let rows = load(input);
    let titles: BTreeMap<_, _> = rows.iter().map(|r| (r.id, r)).collect();
    let mut out = Vec::new();
    for (dir, members) in by_dir(&rows) {
        let top = top_of(dir, &members);
        let title = top.map_or(dir, |t| t.front.title.as_str());
        let top_id = top.map(|t| t.id);
        // Group by the nearest sub-epic parent; everything else is "direct".
        let mut direct: Vec<&Row> = Vec::new();
        let mut subs: BTreeMap<String, Vec<&Row>> = BTreeMap::new();
        for r in members.iter().copied().filter(|r| Some(r.id) != top_id) {
            let sub = r
                .front
                .parent
                .and_then(|p| titles.get(&p))
                .filter(|p| p.front.ty == TicketType::Epic && Some(p.id) != top_id);
            match sub {
                Some(p) => subs
                    .entry(format!("{} ({})", p.front.title, p.handle))
                    .or_default()
                    .push(r),
                None => direct.push(r),
            }
        }
        let mut page = header(
            input,
            title,
            "Tickets of this epic by sub-epic and status. [Back to the front door](../README.md).",
        );
        if let Some(t) = top {
            let _ = writeln!(
                page,
                "Epic ticket: [{}]({EPIC_FILE}) ({}).\n",
                cell(&t.path),
                t.handle
            );
        }
        if !direct.is_empty() {
            let _ = write!(
                page,
                "## Direct ({})\n\n{}",
                direct.len(),
                status_sections(&direct, Some(dir), "###")
            );
        }
        for (name, list) in &subs {
            let _ = write!(
                page,
                "## {} ({})\n\n{}",
                cell(name),
                list.len(),
                status_sections(list, Some(dir), "###")
            );
        }
        out.push((format!("{dir}/{PAGE}"), page.into_bytes()));
    }
    out
}

/// `GEN001` cross-check: every ticket is on exactly one epic page (or the `_unfiled` section of
/// the front door), given the `pages` that [`render`] and [`super::readme::render`] produced.
#[must_use]
pub fn check(input: &GenInput<'_>, pages: &[(String, Vec<u8>)]) -> Vec<CoverageDrift> {
    let rows = load(input);
    let mut drift = Vec::new();
    for r in &rows {
        let (page, dir) = match dir_of(&r.path) {
            Some(d) if d != UNFILED_DIR => (format!("{d}/{PAGE}"), Some(d)),
            _ => (super::readme::PATH.to_owned(), None),
        };
        // The top epic's own ticket is the page header, not a table row.
        if r.path.ends_with(&format!("/{EPIC_FILE}")) && dir.is_some() {
            let linked = pages.iter().any(|(p, b)| {
                *p == page && String::from_utf8_lossy(b).contains(&format!("]({EPIC_FILE})"))
            });
            if !linked {
                drift.push(CoverageDrift::Missing {
                    path: r.path.clone(),
                });
            }
            continue;
        }
        let needle = format!("]({}) |", target(&r.path, dir));
        let count: usize = pages
            .iter()
            .filter(|(p, _)| *p == page)
            .map(|(_, b)| String::from_utf8_lossy(b).matches(&needle).count())
            .sum();
        match count {
            0 => drift.push(CoverageDrift::Missing {
                path: r.path.clone(),
            }),
            1 => {}
            n => drift.push(CoverageDrift::Duplicate {
                path: r.path.clone(),
                count: n,
            }),
        }
    }
    drift
}
