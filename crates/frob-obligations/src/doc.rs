//! DOC001 (undocumented public items) and DOC002 (broken markdown links).

use std::collections::{HashMap, HashSet};
use std::path::{Component, Path, PathBuf};

use frob_tests::catalog::is_test_file;
use gob_languages::{Language, ParseLimits, ParseResult, markdown_link_destinations, parse};
use gob_rules::Finding;
use gob_symbols::{FacetDigest, SymbolGraph, SymbolKind, Target, extract_file, slugify};
use gob_text::{FileId, Span};
use gob_walk::{Digest, FileEntry, LanguageHint};

use crate::rules::{Doc001, Doc002};
use crate::todo::range;
use crate::util::finding;

/// True when an attribute line directly above byte `start` is `#[doc ...]`.
fn has_doc_attribute(text: &str, start: usize) -> bool {
    let Some(before) = text.get(..start) else {
        return false;
    };
    for line in before.trim_end_matches([' ', '\t']).lines().rev() {
        let t = line.trim();
        if t.starts_with("#[doc") {
            return true;
        }
        if !t.starts_with("#[") && !t.starts_with("//") {
            return false;
        }
    }
    false
}

/// DOC001 over one Rust file: public items of `graph` whose doc facet is empty.
pub(crate) fn doc001(graph: &SymbolGraph, file: FileId, path: &str, text: &str) -> Vec<Finding> {
    if Language::detect(path) != Some(Language::Rust) || is_test_file(path) {
        return Vec::new();
    }
    let empty = FacetDigest::of(b"");
    let mut out = Vec::new();
    for rec in graph.public_api() {
        if rec.symref.path() != path
            || rec.kind == SymbolKind::Module
            || rec.implements.is_some()
            || rec.digests.doc != empty
        {
            continue;
        }
        let start = usize::try_from(u32::from(rec.span.start())).unwrap_or(usize::MAX);
        if has_doc_attribute(text, start) {
            continue;
        }
        tracing::debug!(symref = %rec.symref, "undocumented public item");
        out.push(finding(
            &Doc001,
            Some(Span::new(file, rec.span)),
            format!(
                "public {} `{}` has no doc comment",
                format!("{:?}", rec.kind).to_lowercase(),
                rec.symref
            ),
            &rec.symref.to_string(),
        ));
    }
    out
}

/// True when `dest` starts with a URL scheme (`https:`, `mailto:`) or `//`.
fn is_external(dest: &str) -> bool {
    if dest.starts_with("//") {
        return true;
    }
    let Some((scheme, _)) = dest.split_once(':') else {
        return false;
    };
    scheme.starts_with(|c: char| c.is_ascii_alphabetic())
        && scheme
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '+' | '.' | '-'))
}

/// `base_dir` joined with `rel`, normalized; `None` when it escapes the root.
fn resolve(base_dir: &Path, rel: &str) -> Option<PathBuf> {
    let joined = match rel.strip_prefix('/') {
        Some(root_rel) => PathBuf::from(root_rel),
        None => base_dir.join(rel),
    };
    let mut out = PathBuf::new();
    for comp in joined.components() {
        match comp {
            Component::Normal(p) => out.push(p),
            Component::ParentDir if !out.pop() => return None,
            _ => {}
        }
    }
    Some(out)
}

/// Heading slugs of markdown `text` at `path`.
fn heading_slugs(path: &str, text: &str) -> HashSet<String> {
    let entry = FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    extract_file(&entry, text)
        .symbols
        .into_iter()
        .filter_map(|s| match s.symref.target() {
            Target::Anchor(slug) => Some(slug.clone()),
            _ => None,
        })
        .collect()
}

/// Lazily loaded heading slugs of markdown files, keyed by repo-relative path.
struct Anchors<'a> {
    root: &'a Path,
    own_path: &'a str,
    own_text: &'a str,
    cache: HashMap<String, Option<HashSet<String>>>,
}

impl Anchors<'_> {
    /// True when markdown file `path` has a heading whose slug is `slug`; unreadable files count as present.
    fn has(&mut self, path: &str, slug: &str) -> bool {
        let (root, own_path, own_text) = (self.root, self.own_path, self.own_text);
        let slugs = self.cache.entry(path.to_owned()).or_insert_with(|| {
            if path == own_path {
                return Some(heading_slugs(path, own_text));
            }
            std::fs::read_to_string(root.join(path))
                .ok()
                .map(|t| heading_slugs(path, &t))
        });
        slugs.as_ref().is_none_or(|s| s.contains(slug))
    }
}

/// True for markdown paths.
fn is_markdown(path: &str) -> bool {
    Language::detect(path) == Some(Language::Markdown)
}

// frob:ticket 01M3Z712ZXXKVJYREYG65P3P35
/// DOC002 over one markdown file: relative links whose target or anchor does not exist.
pub(crate) fn doc002(root: &Path, file: FileId, path: &str, text: &str) -> Vec<Finding> {
    if !is_markdown(path) {
        return Vec::new();
    }
    let base_dir = Path::new(path).parent().unwrap_or_else(|| Path::new(""));
    let mut anchors = Anchors {
        root,
        own_path: path,
        own_text: text,
        cache: HashMap::new(),
    };
    let mut out = Vec::new();
    let ParseResult::Parsed(tree) = parse(Language::Markdown, text, &ParseLimits::default()) else {
        tracing::warn!(path, "markdown not parsed; DOC002 skipped");
        return out;
    };
    for r in markdown_link_destinations(&tree) {
        let dest = &text[r.clone()];
        if let Some(msg) = check_link(root, base_dir, path, dest, &mut anchors) {
            out.push(finding(
                &Doc002,
                Some(Span::new(file, range(r.start, r.len()))),
                msg,
                &format!("{path}->{dest}"),
            ));
        }
    }
    out
}

/// The problem with link `dest` written in `path`, or `None` when it is fine.
fn check_link(
    root: &Path,
    base_dir: &Path,
    path: &str,
    dest: &str,
    anchors: &mut Anchors<'_>,
) -> Option<String> {
    if is_external(dest) {
        return None;
    }
    let no_query = dest.split('?').next().unwrap_or(dest);
    let (target, anchor) = match no_query.split_once('#') {
        Some((t, a)) => (t, Some(a)),
        None => (no_query, None),
    };
    let resolved = if target.is_empty() {
        PathBuf::from(path)
    } else if let Some(p) = resolve(base_dir, target) {
        p
    } else {
        return Some(format!("link target `{target}` leaves the repository"));
    };
    let rel = resolved.to_string_lossy().replace('\\', "/");
    if !target.is_empty() && !root.join(&resolved).exists() {
        return Some(format!("link target `{target}` does not exist"));
    }
    let anchor = anchor.filter(|a| !a.is_empty())?;
    if !is_markdown(&rel) {
        return None;
    }
    let slug = slugify(anchor);
    if anchors.has(&rel, &slug) {
        None
    } else {
        Some(format!(
            "link anchor `#{anchor}` matches no heading of `{rel}`"
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn destinations_and_schemes() {
        assert!(is_external("https://a.b") && is_external("mailto:a@b"));
        assert!(!is_external("a/b.md") && !is_external("#frag"));
    }

    #[test]
    fn resolve_normalizes_and_rejects_escape() {
        assert_eq!(
            resolve(Path::new("docs"), "../a/./b.md"),
            Some(PathBuf::from("a/b.md"))
        );
        assert_eq!(resolve(Path::new("docs"), "../../x"), None);
        assert_eq!(
            resolve(Path::new("docs"), "/top.md"),
            Some(PathBuf::from("top.md"))
        );
    }
}
