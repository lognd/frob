//! The HTML adapter (fidelity F2): tree-sitter tree to the `gob_ir::markup` forms, inline `style`
//! attributes as `style` declarations, and `<script>` and `<style>` bodies as region islands
//! (language-engines.md sections 2 and 3, D96, D101; universal-model.md 5.1).
//!
//! # Mapping (rho)
//!
//! - The document is a `unit(file, impl)`; its children are the top-level elements, text and holes.
//! - An element is `apply(element)` with a `lit(tag)` head (tag names are lowercased, custom elements
//!   such as `my-card` are intrinsic: HTML has no component references), then `markup.attribute`
//!   nodes (names lowercased; the value is a `lit(str)` with the character references decoded, no value
//!   child means `true`), then text and child elements. Void and implicitly closed elements are
//!   elements like any other. Inter-element whitespace is dropped and text runs are whitespace-collapsed,
//!   so the same queries answer for JSX and HTML ([`gob_ir::markup::elements`], `class_tokens`).
//! - A `style="..."` attribute also carries a `region(css)` child (marked `markup.group = inline-style`)
//!   with one `style.declaration` per declaration, its values tokenised by the shared CSS tokeniser.
//! - A `<script>` body is a `region` child of the element tagged `js` (no `type`, `module`, or a
//!   JavaScript MIME type), `ts` (`lang="ts"`, `text/typescript`), `json` (`application/json`,
//!   `application/ld+json`, `importmap`, `speculationrules`) or `data` (any other `type`, such as a
//!   template); a `<style>` body is a `region(css)`. The region holds the body as one `lit(text)`.
//!   The bodies are islands only: they are not lowered with the TypeScript and CSS adapters (their term
//!   builders are per file, so lowering needs a nested-fold seam; filed as a follow-up).
//! - Comments, the doctype and the extent of the tree are not modelled; syntax errors and stray end
//!   tags are `hole(parse-error)` (or `hole(missing)`), the file is a partial parse.
//! - `crunk:waive` comments are bound by the directive scanner (gob-directives), not here.

// frob:ticket 01M47QKT10CG0RSF784EEYTQ0J

mod entities;

use gob_ir::{NodeId, NodeSpec, Operator, ScopeGraph, TermError, markup};
use gob_languages::{Language, ParseLimits, ParseResult, grammar_identity, parse};
use tree_sitter::Node;

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded, Lang,
};
use crate::css::split_important;
use crate::css::tokens::{declaration_node, tokens};
use crate::fold::{Cx, base_file, children, failed_file, file_root_spec, text_of};
use crate::model::collapse_ws;
use crate::pipeline::EXTRACTOR_VERSION;
use crate::typescript::ATTR_MARKUP_GROUP;
use crate::view::{self, Naming};
use entities::decode;

/// File extensions (lowercase, no dot) the adapter claims.
pub(crate) const EXTENSIONS: &[&str] = &["html", "htm"];

/// Region kind of a `<script>` body written in JavaScript.
const REGION_JS: &str = "js";
/// Region kind of a `<script>` body written in TypeScript.
const REGION_TS: &str = "ts";
/// Region kind of a `<script>` data block holding JSON.
const REGION_JSON: &str = "json";
/// Region kind of a `<script>` body of any other type (templates and the like).
const REGION_DATA: &str = "data";
/// `type` values of a classic or module JavaScript `<script>`.
const JS_TYPES: [&str; 8] = [
    "",
    "module",
    "text/javascript",
    "application/javascript",
    "text/ecmascript",
    "application/ecmascript",
    "text/jsx",
    "babel",
];
/// `type` values of a JSON data block.
const JSON_TYPES: [&str; 5] = [
    "application/json",
    "application/ld+json",
    "importmap",
    "speculationrules",
    "text/json",
];

type R<T> = Result<T, TermError>;

/// The HTML adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct HtmlAdapter;

impl Adapter for HtmlAdapter {
    fn language(&self) -> &'static str {
        "html"
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(Language::Html)
        )
    }

    fn fidelity(&self) -> Fidelity {
        gob_caps::lang_fidelity(Lang::Html)
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::Html)
    }

    fn parse(&self, text: &str, limits: &ParseLimits) -> ConcreteTree {
        match parse(Language::Html, text, limits) {
            ParseResult::Parsed(t) => ConcreteTree::Parsed(t),
            ParseResult::Unresolved(u) => ConcreteTree::Unparsed(u.reason),
        }
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Parsed(t) => fold_tree(&t.text, t.root(), input),
            ConcreteTree::Unparsed(reason) => failed_file(input, "html", *reason),
            ConcreteTree::Leaf | ConcreteTree::Source(_) => failed_file(
                input,
                "html",
                gob_languages::UnresolvedReason::GrammarUnavailable,
            ),
        }
    }
}

/// True when `path` is an HTML file (`.html`, `.htm`, any case).
pub fn is_html_path(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .and_then(|e| e.to_str())
        .is_some_and(|e| EXTENSIONS.iter().any(|x| e.eq_ignore_ascii_case(x)))
}

struct Html<'a> {
    cx: Cx<'a>,
    path: &'a str,
    holes: u32,
}

fn fold_tree(text: &str, root: Node<'_>, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let mut html = Html {
        cx: Cx::new(input.path, "html", text),
        path: input.path,
        holes: 0,
    };
    let mut kids = html.items(root)?;
    if root.has_error() && html.holes == 0 {
        // An error the walk did not reach (inside a tag): the file is still a partial parse.
        kids.push(html.hole(root)?);
    }
    let Html { mut cx, .. } = html;
    let root_id = cx.add(file_root_spec(&cx, input.size as usize), &kids)?;
    let term = cx.b.finish(root_id)?;
    let scopes = ScopeGraph::from_term(&term);
    let v = view::build(&term, input.path, Naming::Opaque);
    let mut file = base_file(input, "html");
    file.fidelity = Fidelity::F2;
    file.parse_status = view::parse_status_of(&term);
    file.symbols = v.symbols;
    file.extras = v.extras;
    tracing::debug!(
        path = input.path,
        status = ?file.parse_status,
        "html file folded"
    );
    Ok(Folded { term, scopes, file })
}

/// The `type`-driven region kind of a `<script>` element with the given attributes.
fn script_region_kind(attrs: &[(String, Option<String>)]) -> &'static str {
    let get = |n: &str| {
        attrs
            .iter()
            .find(|(k, _)| k == n)
            .map(|(_, v)| v.clone().unwrap_or_default().trim().to_ascii_lowercase())
    };
    let ty = get("type").unwrap_or_default();
    if ty == "text/typescript"
        || ty == "application/typescript"
        || get("lang").as_deref() == Some("ts")
    {
        REGION_TS
    } else if JS_TYPES.contains(&ty.as_str()) {
        REGION_JS
    } else if JSON_TYPES.contains(&ty.as_str()) || ty.ends_with("+json") {
        REGION_JSON
    } else {
        REGION_DATA
    }
}

/// Pushes the `prop: value` declaration of `text[from..to]` onto `out` when it has a property name.
fn cut<'t>(text: &'t str, from: usize, to: usize, out: &mut Vec<(usize, &'t str, &'t str)>) {
    if let Some((prop, value)) = text[from..to].split_once(':') {
        let (prop, value) = (prop.trim(), value.trim());
        if !prop.is_empty() {
            out.push((from, prop, value));
        }
    }
}

/// Splits the text of a `style` attribute into `(offset, property, value)` declarations at top-level `;`.
fn split_declarations(text: &str) -> Vec<(usize, &str, &str)> {
    let mut out = Vec::new();
    let (mut start, mut depth, mut quote) = (0usize, 0usize, None::<char>);
    for (i, c) in text.char_indices() {
        match (quote, c) {
            (Some(q), _) if c == q => quote = None,
            (None, '"' | '\'') => quote = Some(c),
            (None, '(') => depth += 1,
            (None, ')') => depth = depth.saturating_sub(1),
            (None, ';') if depth == 0 => {
                cut(text, start, i, &mut out);
                start = i + 1;
            }
            _ => {}
        }
    }
    cut(text, start, text.len(), &mut out);
    out
}

impl Html<'_> {
    fn hole(&mut self, n: Node<'_>) -> R<NodeId> {
        let kind = if n.is_missing() {
            view::HOLE_MISSING
        } else {
            view::HOLE_PARSE_ERROR
        };
        self.holes += 1;
        tracing::debug!(path = self.path, kind, at = n.start_byte(), "html hole");
        self.cx.op(Operator::hole(kind), n, &[])
    }

    fn t(&self, n: Node<'_>) -> &str {
        text_of(self.cx.text, n)
    }

    /// The nodes for the elements, text runs and errors among the children of a document or element.
    fn items(&mut self, parent: Node<'_>) -> R<Vec<NodeId>> {
        let mut out = Vec::new();
        let mut run: Vec<Node<'_>> = Vec::new();
        for c in children(parent) {
            if matches!(c.kind(), "text" | "entity") && !c.is_missing() {
                run.push(c);
                continue;
            }
            self.flush_text(&mut run, &mut out)?;
            let kind = c.kind();
            if c.is_missing() || kind == "ERROR" || kind == "erroneous_end_tag" {
                out.push(self.hole(c)?);
            } else if matches!(kind, "element" | "script_element" | "style_element") {
                out.push(self.element(c)?);
            } else if c.is_named() && !matches!(kind, "comment" | "doctype") {
                tracing::trace!(path = self.path, kind, "html node not modelled");
            }
        }
        self.flush_text(&mut run, &mut out)?;
        Ok(out)
    }

    /// Emits the pending run of text and entity nodes as one `lit(text)`, if anything is left after collapsing.
    fn flush_text(&mut self, run: &mut Vec<Node<'_>>, out: &mut Vec<NodeId>) -> R<()> {
        let (Some(first), Some(last)) = (run.first().copied(), run.last().copied()) else {
            return Ok(());
        };
        let raw = &self.cx.text[first.start_byte()..last.end_byte()];
        let text = collapse_ws(&decode(raw));
        run.clear();
        if text.is_empty() {
            return Ok(());
        }
        let loc = self.cx.loc(first.start_byte(), last.end_byte());
        out.push(
            self.cx
                .add(NodeSpec::new(Operator::lit(markup::TEXT, &text), loc), &[])?,
        );
        Ok(())
    }

    /// One element: head, attributes, then children (or the island of a script or style body).
    fn element(&mut self, n: Node<'_>) -> R<NodeId> {
        let cs = children(n);
        let open = cs
            .iter()
            .find(|c| matches!(c.kind(), "start_tag" | "self_closing_tag"))
            .copied();
        let tag = open
            .and_then(|o| children(o).into_iter().find(|c| c.kind() == "tag_name"))
            .map(|t| self.t(t).to_ascii_lowercase())
            .unwrap_or_default();
        let head = match open {
            Some(o) => {
                let loc = self.cx.node_loc(o);
                self.cx
                    .add(NodeSpec::new(Operator::lit(markup::TAG, &tag), loc), &[])?
            }
            None => self.cx.add(
                NodeSpec::new(Operator::hole(view::HOLE_MISSING), self.cx.node_loc(n)),
                &[],
            )?,
        };
        let mut kids = vec![head];
        let mut attrs = Vec::new();
        if let Some(o) = open {
            for a in children(o).into_iter().filter(|c| c.kind() == "attribute") {
                let (name, value, id) = self.attribute(a)?;
                attrs.push((name, value));
                kids.push(id);
            }
        }
        match n.kind() {
            "script_element" | "style_element" => {
                if let Some(body) = cs
                    .iter()
                    .find(|c| c.kind() == "raw_text" && !c.byte_range().is_empty())
                {
                    let kind = if n.kind() == "style_element" {
                        "css"
                    } else {
                        script_region_kind(&attrs)
                    };
                    tracing::trace!(path = self.path, tag, kind, "html island");
                    kids.push(self.island(*body, kind)?);
                }
            }
            _ => kids.extend(self.items(n)?),
        }
        for c in &cs {
            if c.is_missing() || c.kind() == "ERROR" {
                kids.push(self.hole(*c)?);
            }
        }
        self.cx.add(
            NodeSpec::new(markup::element_op(), self.cx.node_loc(n)),
            &kids,
        )
    }

    /// `region(kind)` over the body text of a script or style element.
    fn island(&mut self, body: Node<'_>, kind: &str) -> R<NodeId> {
        let raw = self.t(body).to_owned();
        let text = self.cx.lit("text", &raw, body)?;
        self.cx.op(Operator::region(kind), body, &[text])
    }

    /// One attribute: its lowercased name, decoded value if written, and its node.
    fn attribute(&mut self, a: Node<'_>) -> R<(String, Option<String>, NodeId)> {
        let cs = children(a);
        let name = cs
            .iter()
            .find(|c| c.kind() == "attribute_name")
            .map(|c| self.t(*c).to_ascii_lowercase())
            .unwrap_or_default();
        let has_value = cs.iter().any(|c| c.kind() == "=");
        let value_node = cs.iter().find_map(|c| match c.kind() {
            "attribute_value" => Some((*c, c.start_byte(), c.end_byte())),
            "quoted_attribute_value" => {
                let inner = children(*c)
                    .into_iter()
                    .find(|k| k.kind() == "attribute_value");
                Some(match inner {
                    Some(i) => (*c, i.start_byte(), i.end_byte()),
                    // `a=""`: the span between the quotes is empty.
                    None => (
                        *c,
                        c.start_byte() + 1,
                        c.end_byte().saturating_sub(1).max(c.start_byte() + 1),
                    ),
                })
            }
            _ => None,
        });
        let mut kids = Vec::new();
        let mut value = None;
        if has_value {
            let (raw_start, raw_end) =
                value_node.map_or((a.end_byte(), a.end_byte()), |(_, s, e)| (s, e));
            let raw = &self.cx.text[raw_start..raw_end];
            let decoded = decode(raw);
            let loc = self.cx.loc(raw_start, raw_end);
            kids.push(
                self.cx
                    .add(NodeSpec::new(Operator::lit("str", &decoded), loc), &[])?,
            );
            if name == "style" {
                kids.push(self.inline_style(raw, raw_start)?);
            }
            value = Some(decoded);
        }
        let spec = NodeSpec::new(markup::attribute_op(), self.cx.node_loc(a)).named(&name);
        let id = self.cx.add(spec, &kids)?;
        Ok((name, value, id))
    }

    /// The `region(css)` island of a `style` attribute value starting at byte `base`.
    fn inline_style(&mut self, raw: &str, base: usize) -> R<NodeId> {
        let mut decls = Vec::new();
        for (off, prop, value) in split_declarations(raw) {
            let property = if prop.starts_with("--") {
                prop.to_owned()
            } else {
                prop.to_ascii_lowercase()
            };
            let decoded = decode(value);
            let (body, important) = split_important(&decoded);
            let end = (off + prop.len() + value.len() + 1).min(raw.len());
            let loc = self.cx.loc(base + off, base + end);
            decls.push(declaration_node(
                &mut self.cx,
                loc,
                &property,
                body,
                important,
                tokens(body),
            )?);
        }
        tracing::trace!(path = self.path, decls = decls.len(), "html inline style");
        let loc = self.cx.loc(base, base + raw.len());
        let spec =
            NodeSpec::new(Operator::region("css"), loc).attr(ATTR_MARKUP_GROUP, "inline-style");
        self.cx.add(spec, &decls)
    }
}
