//! Orphan pages: documents under `docs/` that no chain of links from a root page reaches.
//!
//! Broken links and anchors are DOC002's job; this module reuses the same link extraction and path
//! folding as the remap so the two agree on what a link means.

// frob:ticket 01M67VEKBESFK2C23JMXV82RW9

use std::collections::{BTreeMap, BTreeSet, VecDeque};

use gob_languages::{Language, ParseLimits, ParseResult, markdown_link_destinations, parse};
use gob_symbols::{DocStatus, is_generated, parse_header};

use crate::rewrite::{dir_of, normalize};

/// The directory whose pages must be reachable.
const DOCS_DIR: &str = "docs/";
/// The docs entry page, a root alongside every markdown file outside `docs/`.
const DOCS_INDEX: &str = "docs/README.md";
/// File names a link to a directory lands on.
const DIR_INDEXES: &[&str] = &["README.md", "index.md"];

/// One markdown page: its repo-relative path and text.
#[derive(Debug, Clone, Copy)]
pub struct Page<'a> {
    /// Repo-relative path with forward slashes.
    pub path: &'a str,
    /// The page text.
    pub text: &'a str,
}

/// A page whose markdown did not parse, so its links are unknown.
#[derive(Debug, thiserror::Error)]
#[error("markdown of `{0}` did not parse; its links are unknown")]
pub struct Unparsed(pub String);

/// True when `page` may be an orphan: under `docs/`, hand-written and not retired (superseded or historical).
fn must_be_reachable(page: &Page<'_>) -> bool {
    if !page.path.starts_with(DOCS_DIR) || page.path == DOCS_INDEX || is_generated(page.text) {
        return false;
    }
    !matches!(
        parse_header(page.text).status,
        Ok(DocStatus::SupersededBy(_) | DocStatus::Historical)
    )
}

/// The pages a link `dest` written in `from` can name, as repo-relative paths (not yet checked to exist).
fn targets(from: &str, dest: &str) -> Vec<String> {
    if dest.contains("://") || dest.starts_with("mailto:") {
        return Vec::new();
    }
    let file = dest.split(['#', '?']).next().unwrap_or("");
    if file.is_empty() {
        return Vec::new();
    }
    let norm = if let Some(rooted) = file.strip_prefix('/') {
        normalize("", rooted)
    } else {
        normalize(dir_of(from), file)
    };
    let Some(norm) = norm else { return Vec::new() };
    let mut out = vec![norm.clone()];
    out.extend(DIR_INDEXES.iter().map(|i| format!("{norm}/{i}")));
    out
}

/// The repo-relative paths of `page`'s link targets, or `Unparsed` when its markdown does not parse.
fn links(page: &Page<'_>) -> Result<Vec<String>, Unparsed> {
    let ParseResult::Parsed(tree) = parse(Language::Markdown, page.text, &ParseLimits::default())
    else {
        return Err(Unparsed(page.path.to_owned()));
    };
    Ok(markdown_link_destinations(&tree)
        .into_iter()
        .flat_map(|r| targets(page.path, &page.text[r]))
        .collect())
}

/// Paths of `docs/` pages that no link chain from a root page reaches, sorted.
///
/// Roots are every markdown page outside `docs/` plus `docs/README.md`; generated, `historical`
/// and `superseded-by` pages are exempt. Fails when a page's markdown does not parse, since its links
/// are then unknown and any answer could be a false orphan.
///
/// # Errors
///
/// [`Unparsed`] names the first page whose markdown could not be parsed.
pub fn orphans(pages: &[Page<'_>]) -> Result<Vec<String>, Unparsed> {
    let by_path: BTreeMap<&str, &Page<'_>> = pages.iter().map(|p| (p.path, p)).collect();
    let mut seen: BTreeSet<&str> = BTreeSet::new();
    let mut queue: VecDeque<&Page<'_>> = pages
        .iter()
        .filter(|p| !p.path.starts_with(DOCS_DIR) || p.path == DOCS_INDEX)
        .collect();
    seen.extend(queue.iter().map(|p| p.path));
    while let Some(page) = queue.pop_front() {
        for target in links(page)? {
            if let Some((path, next)) = by_path.get_key_value(target.as_str())
                && seen.insert(path)
            {
                queue.push_back(next);
            }
        }
    }
    let found: Vec<String> = pages
        .iter()
        .filter(|p| must_be_reachable(p) && !seen.contains(p.path))
        .map(|p| p.path.to_owned())
        .collect();
    tracing::debug!(
        pages = pages.len(),
        orphans = found.len(),
        "orphan scan done"
    );
    let mut found = found;
    found.sort();
    Ok(found)
}
