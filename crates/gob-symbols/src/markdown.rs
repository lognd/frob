//! Markdown extraction: headings as `path#slug` anchors.

use std::collections::HashMap;

use gob_languages::ParsedTree;
use tree_sitter::Node;

use crate::model::{Digests, FileSymbols, SymbolKind, SymbolRecord, Visibility, collapse_ws};
use crate::symref::Symref;

/// GitHub-style slug of heading text, before duplicate suffixing.
///
/// Lowercases, drops everything but alphanumerics, spaces, hyphens and
/// underscores, then turns spaces into hyphens. Link syntax keeps only the
/// link text and inline-code backticks are dropped.
pub fn slugify(heading: &str) -> String {
    let flat = strip_links(heading);
    flat.trim()
        .chars()
        .filter_map(|c| {
            if c.is_alphanumeric() || c == '-' || c == '_' {
                Some(c.to_lowercase().collect::<String>())
            } else if c == ' ' {
                Some("-".to_owned())
            } else {
                None
            }
        })
        .collect()
}

/// Rewrites `[text](url)` to `text`.
fn strip_links(s: &str) -> String {
    let mut out = String::new();
    let mut rest = s;
    while let Some(open) = rest.find('[') {
        let Some(close_rel) = rest[open..].find("](") else {
            break;
        };
        let close = open + close_rel;
        let Some(end_rel) = rest[close..].find(')') else {
            break;
        };
        out.push_str(&rest[..open]);
        out.push_str(&rest[open + 1..close]);
        rest = &rest[close + end_rel + 1..];
    }
    out.push_str(rest);
    out
}

struct Heading<'t> {
    section: Node<'t>,
    text: String,
    body_start: usize,
    parent: Option<usize>,
}

/// Extracts one symbol per heading.
pub fn extract(tree: &ParsedTree, path: &str, mut out: FileSymbols) -> FileSymbols {
    let mut headings: Vec<Heading<'_>> = Vec::new();
    collect(tree, tree.root(), None, &mut headings);

    let mut used: HashMap<String, usize> = HashMap::new();
    let mut refs: Vec<Option<Symref>> = Vec::with_capacity(headings.len());
    for h in &headings {
        let base = slugify(&h.text);
        if base.is_empty() {
            tracing::debug!(path, "heading with empty slug skipped");
            refs.push(None);
            continue;
        }
        let n = used.entry(base.clone()).or_default();
        let slug = if *n == 0 {
            base.clone()
        } else {
            format!("{base}-{n}")
        };
        *n += 1;
        // A suffixed slug can collide with a later literal heading; reserve it.
        if slug != base {
            used.entry(slug.clone()).or_insert(1);
        }
        refs.push(Some(Symref::anchor(path, &slug)));
    }
    for (h, symref) in headings.iter().zip(&refs) {
        let Some(symref) = symref else { continue };
        let start = h.section.start_byte();
        let end = h.section.end_byte();
        let body = collapse_ws(&tree.text[h.body_start.min(end)..end]);
        let sig = collapse_ws(&h.text);
        let clamp = |n: usize| gob_text::TextSize::new(u32::try_from(n).unwrap_or(u32::MAX));
        let parent = h.parent.and_then(|p| refs[p].clone());
        tracing::trace!(%symref, "markdown heading");
        out.symbols.push(SymbolRecord {
            symref: symref.clone(),
            kind: SymbolKind::Heading,
            span: gob_text::TextRange::new(clamp(start), clamp(end)),
            visibility: Visibility::Public,
            digests: Digests::of_facets(&sig, &body, ""),
            parent,
            implements: None,
        });
    }
    out
}

fn collect<'t>(
    tree: &'t ParsedTree,
    node: Node<'t>,
    parent: Option<usize>,
    out: &mut Vec<Heading<'t>>,
) {
    let mut c = node.walk();
    let kids: Vec<Node<'t>> = node.named_children(&mut c).collect();
    for k in kids {
        if k.kind() != "section" {
            continue;
        }
        let mut cc = k.walk();
        let heading = k
            .named_children(&mut cc)
            .find(|n| matches!(n.kind(), "atx_heading" | "setext_heading"));
        let mut next_parent = parent;
        if let Some(h) = heading {
            let text = heading_text(tree, h);
            out.push(Heading {
                section: k,
                text,
                body_start: h.end_byte(),
                parent,
            });
            next_parent = Some(out.len() - 1);
        }
        collect(tree, k, next_parent, out);
    }
}

fn heading_text(tree: &ParsedTree, h: Node<'_>) -> String {
    let mut c = h.walk();
    let inner = h
        .named_children(&mut c)
        .find(|n| matches!(n.kind(), "inline" | "paragraph"));
    let raw = inner.map_or("", |n| &tree.text[n.start_byte()..n.end_byte()]);
    collapse_ws(raw)
}

#[cfg(test)]
mod tests {
    use super::slugify;

    #[test]
    fn github_slugs() {
        assert_eq!(slugify("Hello, World!"), "hello-world");
        assert_eq!(slugify("The `foo` API"), "the-foo-api");
        assert_eq!(slugify("See [docs](http://x.y)"), "see-docs");
        assert_eq!(slugify("a_b - c"), "a_b---c");
    }
}
