//! The markdown adapter (fidelity F4): sections as units, links as `apply(link)`.
//!
//! # Mapping (rho)
//!
//! - The document is `unit(file, impl)`; every heading with a non-empty slug is a
//!   `unit(section, impl)` named by its GitHub-style slug (deduplicated with `-N`),
//!   a flat child of the document so that a section's Body facet is section-local
//!   (G9). The parent section is the attribute `section.parent`, the level the
//!   attribute `level`; the legacy symref is `path#slug`.
//! - A section's Sig facet is its heading text; its Body facet is its own blocks
//!   (nested sections excluded) with prose whitespace collapsed and code exact. The
//!   subtree digest over the section and everything nested is a separate fact
//!   ([`crate::UnitExtras::subtree`]).
//! - Inline links `[text](dest)` and reference definitions `[x]: dest` are
//!   `apply(link)` over `ref(dest)`; they are also [`crate::RefSite`]s so the graph
//!   can resolve them against anchors (Must) or report them broken (Unknown).
//! - Block structure maps to the adapter operators `markdown.<kind>`; leaves are
//!   `lit`s.

// frob:ticket 01M3Z713F6VY15YSMS15033RN1

use std::collections::HashMap;

use gob_ir::{GroupOrder, NodeId, NodeSpec, Operator, ScopeGraph, Sort, TermError, reserved};
use gob_languages::{Language, ParseLimits, ParseResult, grammar_identity, parse};
use tree_sitter::Node;

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded, Lang,
};
use crate::fold::{Cx, base_file, failed_file, file_root_spec};
use crate::model::{RefKind, RefSite, collapse_ws};
use crate::pipeline::EXTRACTOR_VERSION;
use crate::symref::Symref;
use crate::view::{self, ATTR_SECTION_PARENT, Naming};

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

type R<T> = Result<T, TermError>;

/// The markdown adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct MarkdownAdapter;

impl Adapter for MarkdownAdapter {
    fn language(&self) -> &'static str {
        "markdown"
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(Language::Markdown)
        )
    }

    fn fidelity(&self) -> Fidelity {
        gob_caps::lang_fidelity(Lang::Markdown)
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::Markdown)
    }

    fn parse(&self, text: &str, limits: &ParseLimits) -> ConcreteTree {
        match parse(Language::Markdown, text, limits) {
            ParseResult::Parsed(t) => ConcreteTree::Parsed(t),
            ParseResult::Unresolved(u) => ConcreteTree::Unparsed(u.reason),
        }
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Parsed(t) => fold_tree(&t.text, t.root(), input),
            ConcreteTree::Unparsed(reason) => failed_file(input, "markdown", *reason),
            ConcreteTree::Leaf | ConcreteTree::Source(_) => failed_file(
                input,
                "markdown",
                gob_languages::UnresolvedReason::GrammarUnavailable,
            ),
        }
    }
}

struct LinkSite {
    /// Index into the section unit list; `None` for the document preamble.
    section: Option<usize>,
    dest: String,
}

struct Md<'a> {
    cx: Cx<'a>,
    used: HashMap<String, usize>,
    /// Section unit ids in document order.
    sections: Vec<NodeId>,
    links: Vec<LinkSite>,
}

fn children(n: Node<'_>) -> Vec<Node<'_>> {
    let mut c = n.walk();
    n.children(&mut c).collect()
}

fn heading_level(h: Node<'_>) -> i64 {
    for c in children(h) {
        if let Some(d) = c.kind().chars().find(char::is_ascii_digit)
            && (c.kind().starts_with("atx_h") || c.kind().starts_with("setext_h"))
        {
            return i64::from(d.to_digit(10).unwrap_or(1));
        }
    }
    1
}

fn fold_tree(text: &str, root: Node<'_>, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let mut md = Md {
        cx: Cx::new(input.path, "markdown", text),
        used: HashMap::new(),
        sections: Vec::new(),
        links: Vec::new(),
    };
    let mut preamble = Vec::new();
    let mut units = Vec::new();
    md.document(root, &mut preamble, &mut units)?;
    let mut kids = units;
    kids.extend(preamble);
    let root_id = md
        .cx
        .add(file_root_spec(&md.cx, input.size as usize), &kids)?;
    let Md {
        cx,
        sections,
        links,
        ..
    } = md;
    let term = cx.b.finish(root_id)?;
    let scopes = ScopeGraph::from_term(&term);
    let v = view::build(&term, input.path, Naming::Markdown);
    let mut file = base_file(input, "markdown");
    file.fidelity = Fidelity::F4;
    file.parse_status = view::parse_status_of(&term);
    for l in links {
        let from = match l.section.and_then(|i| sections.get(i)) {
            Some(n) => v.by_node.get(n).cloned(),
            None => Some(Symref::file(input.path)),
        };
        if let Some(from) = from {
            file.refs.push(RefSite {
                from,
                name: l.dest,
                qualifier: None,
                kind: RefKind::Link,
            });
        }
    }
    file.symbols = v.symbols;
    file.extras = v.extras;
    tracing::debug!(
        path = input.path,
        sections = file.symbols.len(),
        links = file.refs.len(),
        status = ?file.parse_status,
        "markdown file folded"
    );
    Ok(Folded { term, scopes, file })
}

impl Md<'_> {
    fn t(&self, n: Node<'_>) -> &str {
        &self.cx.text[n.start_byte()..n.end_byte()]
    }

    fn document(
        &mut self,
        node: Node<'_>,
        sink: &mut Vec<NodeId>,
        units: &mut Vec<NodeId>,
    ) -> R<()> {
        for k in children(node) {
            if k.kind() == "section" {
                self.section(k, None, sink, units)?;
            } else {
                self.block(k, None, sink)?;
            }
        }
        Ok(())
    }

    fn slug(&mut self, text: &str) -> Option<String> {
        let base = slugify(text);
        if base.is_empty() {
            return None;
        }
        let n = self.used.entry(base.clone()).or_default();
        let slug = if *n == 0 {
            base.clone()
        } else {
            format!("{base}-{n}")
        };
        *n += 1;
        // A suffixed slug can collide with a later literal heading; reserve it.
        if slug != base {
            self.used.entry(slug.clone()).or_insert(1);
        }
        Some(slug)
    }

    /// Folds one `section`; `sink` receives blocks of an unnamed heading, `units`
    /// receives this section's unit and then those of its nested sections.
    fn section(
        &mut self,
        sec: Node<'_>,
        parent: Option<&(usize, String)>,
        sink: &mut Vec<NodeId>,
        units: &mut Vec<NodeId>,
    ) -> R<()> {
        let kids = children(sec);
        let heading = kids
            .iter()
            .copied()
            .find(|n| matches!(n.kind(), "atx_heading" | "setext_heading"));
        let slug = heading.and_then(|h| {
            let text = heading_text(self.cx.text, h);
            self.slug(&text).map(|s| (s, text))
        });
        let Some((slug, text)) = slug else {
            tracing::debug!(
                at = sec.start_byte(),
                "heading with empty slug: content merged up"
            );
            for k in kids {
                match k.kind() {
                    "section" => self.section(k, parent, sink, units)?,
                    _ => self.block(k, parent.map(|p| p.0), sink)?,
                }
            }
            return Ok(());
        };
        let idx = self.sections.len();
        // Reserve the slot: the unit id is known only after its children exist.
        let mut body = Vec::new();
        let mut nested: Vec<Node<'_>> = Vec::new();
        for k in &kids {
            match k.kind() {
                "section" => nested.push(*k),
                _ if heading.is_some_and(|h| h.id() == k.id()) => {
                    self.heading_links(*k, idx, &mut body)?;
                }
                _ => self.block(*k, Some(idx), &mut body)?,
            }
        }
        let level = heading.map_or(1, heading_level);
        let sig_text = self
            .cx
            .lit("heading", &collapse_ws(&text), heading.unwrap_or(sec))?;
        let sig_spec = NodeSpec::new(Operator::group(GroupOrder::Sequence), self.cx.node_loc(sec))
            .attr(reserved::FACET, "sig");
        let sig = self.cx.add(sig_spec, &[sig_text])?;
        let mut children_ids = vec![sig];
        children_ids.extend(body);
        let mut unit_spec = NodeSpec::new(Operator::unit("section", "impl"), self.cx.node_loc(sec))
            .named(&slug)
            .attr("level", level);
        if let Some((_, p)) = parent {
            unit_spec = unit_spec.attr(ATTR_SECTION_PARENT, p.as_str());
        }
        let id = self.cx.add(unit_spec, &children_ids)?;
        self.sections.push(id);
        units.push(id);
        for n in nested {
            self.section(n, Some(&(idx, slug.clone())), sink, units)?;
        }
        Ok(())
    }

    fn heading_links(&mut self, h: Node<'_>, idx: usize, out: &mut Vec<NodeId>) -> R<()> {
        for c in children(h) {
            if matches!(c.kind(), "inline" | "paragraph") {
                let text = self.t(c).to_owned();
                self.links_in(&text, c, Some(idx), out)?;
            }
        }
        Ok(())
    }

    fn links_in(
        &mut self,
        text: &str,
        at: Node<'_>,
        section: Option<usize>,
        out: &mut Vec<NodeId>,
    ) -> R<()> {
        for (label, dest) in scan_links(text) {
            let head = self.cx.op(Operator::reference(&dest), at, &[])?;
            let lab = self.cx.lit("text", &collapse_ws(&label), at)?;
            out.push(self.cx.op(Operator::apply("link"), at, &[head, lab])?);
            self.links.push(LinkSite { section, dest });
        }
        Ok(())
    }

    /// Translates one block node into `out` (leaves exact, prose whitespace collapsed).
    fn block(&mut self, n: Node<'_>, section: Option<usize>, out: &mut Vec<NodeId>) -> R<()> {
        match n.kind() {
            "block_continuation" => return Ok(()),
            "ERROR" => {
                out.push(self.cx.op(Operator::hole(view::HOLE_PARSE_ERROR), n, &[])?);
                return Ok(());
            }
            "link_reference_definition" => {
                let dest = children(n)
                    .into_iter()
                    .find(|c| c.kind() == "link_destination")
                    .map(|c| self.t(c).trim_matches(['<', '>']).to_owned());
                let label = children(n)
                    .into_iter()
                    .find(|c| c.kind() == "link_label")
                    .map(|c| self.t(c).to_owned());
                if let Some(dest) = dest {
                    let head = self.cx.op(Operator::reference(&dest), n, &[])?;
                    let lab = self.cx.lit("text", label.as_deref().unwrap_or(""), n)?;
                    out.push(self.cx.op(Operator::apply("link"), n, &[head, lab])?);
                    self.links.push(LinkSite { section, dest });
                }
                return Ok(());
            }
            _ => {}
        }
        let text_leaf = matches!(
            n.kind(),
            "inline" | "code_fence_content" | "info_string" | "indented_code_block"
        );
        if n.child_count() == 0 || text_leaf {
            let raw = self.t(n).to_owned();
            if n.kind() == "inline" {
                out.push(self.cx.lit("inline", &collapse_ws(&raw), n)?);
                self.links_in(&raw, n, section, out)?;
            } else {
                out.push(self.cx.lit(n.kind(), &raw, n)?);
            }
            return Ok(());
        }
        let mut kids = Vec::new();
        for c in children(n) {
            self.block(c, section, &mut kids)?;
        }
        let op = Operator::adapter("markdown", n.kind(), Sort::Exp);
        out.push(self.cx.op(op, n, &kids)?);
        Ok(())
    }
}

fn heading_text(text: &str, h: Node<'_>) -> String {
    let mut c = h.walk();
    let inner = h
        .named_children(&mut c)
        .find(|n| matches!(n.kind(), "inline" | "paragraph"));
    let raw = inner.map_or("", |n| &text[n.start_byte()..n.end_byte()]);
    collapse_ws(raw)
}

/// Inline links and images `[text](dest "title")` in `text`, code spans skipped.
fn scan_links(text: &str) -> Vec<(String, String)> {
    let b = text.as_bytes();
    let mut out = Vec::new();
    let mut i = 0;
    while i < b.len() {
        match b[i] {
            b'\\' => i += 2,
            b'`' => {
                let run = b[i..].iter().take_while(|&&c| c == b'`').count();
                let fence = &text[i..i + run];
                match text[i + run..].find(fence) {
                    Some(end) => i += run + end + run,
                    None => i += run,
                }
            }
            b'[' => {
                let mut depth = 0usize;
                let mut j = i;
                let mut close = None;
                while j < b.len() {
                    match b[j] {
                        b'\\' => j += 1,
                        b'[' => depth += 1,
                        b']' => {
                            depth -= 1;
                            if depth == 0 {
                                close = Some(j);
                                break;
                            }
                        }
                        _ => {}
                    }
                    j += 1;
                }
                let Some(close) = close else { break };
                if b.get(close + 1) == Some(&b'(') {
                    let mut pd = 0usize;
                    let mut k = close + 1;
                    let mut end = None;
                    while k < b.len() {
                        match b[k] {
                            b'\\' => k += 1,
                            b'(' => pd += 1,
                            b')' => {
                                pd -= 1;
                                if pd == 0 {
                                    end = Some(k);
                                    break;
                                }
                            }
                            _ => {}
                        }
                        k += 1;
                    }
                    if let Some(end) = end {
                        let inner = text[close + 2..end].trim();
                        let dest = inner
                            .split_whitespace()
                            .next()
                            .unwrap_or("")
                            .trim_matches(['<', '>']);
                        if !dest.is_empty() {
                            out.push((text[i + 1..close].to_owned(), dest.to_owned()));
                        }
                        i = end + 1;
                        continue;
                    }
                }
                // Not a link: look inside the brackets for nested links.
                i += 1;
            }
            _ => i += 1,
        }
    }
    out
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
