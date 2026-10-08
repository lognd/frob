//! One CSS file's text to its located facts: declarations, selectors, custom properties,
//! waivers and media queries (the Python `ingest.parse`).
//!
//! Structure comes from the shared CSS adapter (`gob-symbols`); value-level facts come from
//! this crate's tokenizer, because the adapter's component values are too coarse for per-token
//! spans. Waivers come from the shared directive scanner.

// frob:ticket 01M43ARY91XZ35DN9SCHRHS033

use std::collections::HashMap;
use std::sync::OnceLock;

use gob_directives::{Directive, ScanConfig, Scanner};
use gob_ir::{Location, Model, NodeId, style};
use gob_languages::Language;
use gob_symbols::fold_file;
use gob_walk::FileEntry;
use serde::{Deserialize, Serialize};

use crate::facts::{channel_triplet, value_facts};
use crate::lex::{Kind, Tok, inner_tokens, split_dimension, tokenize, unescape};
use crate::model::{ClassSelector, CustomProp, Declaration, LocatedMediaQuery, Span, Waiver};
use crate::waive::Waive;

/// At-rules whose block holds style rules of their own, so the walk recurses into them.
const GROUP_AT_RULES: [&str; 6] = [
    "media",
    "supports",
    "layer",
    "container",
    "scope",
    "starting-style",
];

/// Why a file could not be folded at all (an adapter bug, never bad CSS).
#[derive(Debug, thiserror::Error)]
#[error("cannot fold {path}: {detail}")]
pub struct FoldFailure {
    /// The file.
    pub path: String,
    /// The adapter's error text.
    pub detail: String,
}

/// Everything parsed from one CSS file; the cacheable unit.
#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
pub struct ParsedCss {
    /// Declarations (custom property definitions included) in source order.
    pub declarations: Vec<Declaration>,
    /// Class selectors in source order.
    pub class_selectors: Vec<ClassSelector>,
    /// `--x:` definition sites in source order.
    pub custom_props: Vec<CustomProp>,
    /// Waivers that attached to no declaration.
    pub orphan_waivers: Vec<Waiver>,
    /// `@media` preludes in source order, outer before inner.
    pub media_queries: Vec<LocatedMediaQuery>,
    /// Parse errors and malformed directives, as messages.
    pub errors: Vec<String>,
}

/// Byte offsets of line starts, with CSS newline rules (`\n`, `\r\n`, `\r`, form feed).
struct Lines(Vec<usize>);

impl Lines {
    fn of(src: &str) -> Self {
        let mut starts = vec![0];
        let bytes = src.as_bytes();
        let mut i = 0;
        while i < bytes.len() {
            match bytes[i] {
                b'\r' if bytes.get(i + 1) == Some(&b'\n') => {
                    i += 2;
                    starts.push(i);
                }
                b'\n' | b'\r' | 0x0c => {
                    i += 1;
                    starts.push(i);
                }
                _ => i += 1,
            }
        }
        Self(starts)
    }

    /// The 1-based line holding byte `offset`.
    fn line_of(&self, offset: usize) -> u32 {
        let idx = self.0.partition_point(|&s| s <= offset);
        u32::try_from(idx).unwrap_or(u32::MAX)
    }
}

fn scanner() -> &'static Scanner {
    static SCANNER: OnceLock<Scanner> = OnceLock::new();
    SCANNER.get_or_init(|| {
        Scanner::new(&ScanConfig {
            namespaces: vec!["crunk".to_owned()],
            product: "crunk".to_owned(),
        })
    })
}

struct Walker<'a> {
    source: &'a str,
    lines: Lines,
    root_font_size: f64,
    model: &'a Model,
    declarations: HashMap<NodeId, style::Declaration>,
    customs: HashMap<NodeId, style::CustomProperty>,
    rules: HashMap<NodeId, style::StyleRule>,
    at_rules: HashMap<NodeId, style::AtRule>,
    out: ParsedCss,
}

fn text_range(model: &Model, node: NodeId) -> Option<(usize, usize)> {
    match model.term().node(node).location() {
        Location::Text { range, .. } => Some((
            u32::from(range.start()) as usize,
            u32::from(range.end()) as usize,
        )),
        _ => None,
    }
}

impl Walker<'_> {
    fn visit_children(&mut self, node: NodeId) {
        let kids: Vec<NodeId> = self.model.term().node(node).children().to_vec();
        for kid in kids {
            self.visit(kid);
        }
    }

    fn visit(&mut self, node: NodeId) {
        if let Some(d) = self.declarations.remove(&node) {
            self.declaration(node, &d.property);
        } else if let Some(c) = self.customs.remove(&node) {
            self.declaration(node, &c.name);
        } else if self.rules.contains_key(&node) {
            self.style_rule(node);
        } else if let Some(at) = self.at_rules.get(&node).cloned() {
            self.at_rule(node, &at);
        }
    }

    fn style_rule(&mut self, node: NodeId) {
        let Some((start, end)) = text_range(self.model, node) else {
            return;
        };
        let text = &self.source[start..end];
        let toks = tokenize(text);
        let prelude_end = toks
            .iter()
            .position(|t| t.kind == Kind::Block('{'))
            .unwrap_or(toks.len());
        for (i, tok) in toks[..prelude_end].iter().enumerate() {
            if tok.kind == Kind::Literal
                && tok.text(text) == "."
                && toks.get(i + 1).is_some_and(|n| n.kind == Kind::Ident)
            {
                self.out.class_selectors.push(ClassSelector {
                    name: unescape(toks[i + 1].text(text)),
                    line: self.lines.line_of(start + tok.start),
                });
            }
        }
        self.visit_children(node);
    }

    fn at_rule(&mut self, node: NodeId, at: &style::AtRule) {
        let name = at.name.to_ascii_lowercase();
        if !GROUP_AT_RULES.contains(&name.as_str()) {
            tracing::debug!(at_rule = %name, "ingest: skipping at-rule contents");
            return;
        }
        let Some((start, end)) = text_range(self.model, node) else {
            return;
        };
        let text = &self.source[start..end];
        let toks = tokenize(text);
        let Some(block) = toks.iter().position(|t| t.kind == Kind::Block('{')) else {
            return;
        };
        if name == "media" {
            let from = toks.first().map_or(0, |t| t.end);
            let prelude = text[from..toks[block].start].trim();
            self.out
                .media_queries
                .push(media_query(prelude, self.lines.line_of(start)));
        }
        self.visit_children(node);
    }

    fn declaration(&mut self, node: NodeId, property: &str) {
        let Some((start, end)) = text_range(self.model, node) else {
            return;
        };
        let text = &self.source[start..end];
        let Some(colon) = text.find(':') else {
            tracing::debug!(property, "ingest: declaration without a colon skipped");
            return;
        };
        let rest_off = start + colon + 1;
        let rest = &text[colon + 1..];
        let mut toks = tokenize(rest);
        if let Some(semi) = toks
            .iter()
            .position(|t| t.kind == Kind::Literal && t.text(rest) == ";")
        {
            toks.truncate(semi);
        }
        strip_important(rest, &mut toks);
        let significant: Vec<&Tok> = toks.iter().filter(|t| !t.is_trivia()).collect();
        let prop = property.to_ascii_lowercase();
        let line = self.lines.line_of(start);
        let (span, value, mut facts): (Span, String, _) =
            match (significant.first(), significant.last()) {
                (Some(first), Some(last)) => {
                    let span = (rest_off + first.start, rest_off + last.end);
                    let value = self.source[span.0..span.1].to_owned();
                    let facts =
                        value_facts(&self.source[span.0..span.1], span.0, self.root_font_size);
                    (span, value, facts)
                }
                _ => ((0, 0), String::new(), crate::facts::ValueFacts::default()),
            };
        if prop.starts_with("--")
            && span != (0, 0)
            && let Some(color) = channel_triplet(&value, span)
        {
            facts.colors.push(color);
        }
        if prop.starts_with("--") {
            self.out.custom_props.push(CustomProp {
                name: prop.clone(),
                line,
            });
        }
        self.out.declarations.push(Declaration {
            prop,
            value,
            line,
            span,
            waivers: Vec::new(),
            colors: facts.colors,
            lengths: facts.lengths,
            var_refs: facts.var_refs,
        });
    }
}

/// Drop a trailing `! important` (and the trivia before it) from the declaration value tokens.
fn strip_important(src: &str, toks: &mut Vec<Tok>) {
    let sig: Vec<usize> = toks
        .iter()
        .enumerate()
        .filter(|(_, t)| !t.is_trivia())
        .map(|(i, _)| i)
        .collect();
    if let [.., bang, imp] = sig[..]
        && toks[bang].kind == Kind::Literal
        && toks[bang].text(src) == "!"
        && toks[imp].kind == Kind::Ident
        && toks[imp].text(src).eq_ignore_ascii_case("important")
    {
        toks.truncate(bang);
    }
}

/// The first literal `min-width` and `max-width` px values among `toks`, descending into `(...)`.
fn feature_widths(src: &str, toks: &[Tok]) -> (Option<f64>, Option<f64>) {
    let (mut min_px, mut max_px) = (None, None);
    for (i, tok) in toks.iter().enumerate() {
        match tok.kind {
            Kind::Block('(') => {
                let inner = inner_tokens(src, tok);
                let (a, b) = feature_widths(src, &inner);
                min_px = min_px.or(a);
                max_px = max_px.or(b);
            }
            Kind::Ident => {
                let name = tok.text(src).to_ascii_lowercase();
                if name != "min-width" && name != "max-width" {
                    continue;
                }
                let mut rest = toks[i + 1..].iter().filter(|t| !t.is_trivia());
                let (Some(colon), Some(dim)) = (rest.next(), rest.next()) else {
                    continue;
                };
                if colon.kind != Kind::Literal
                    || colon.text(src) != ":"
                    || dim.kind != Kind::Dimension
                {
                    continue;
                }
                let (num, unit) = split_dimension(dim.text(src));
                if !unit.eq_ignore_ascii_case("px") {
                    continue;
                }
                if let Ok(px) = num.parse::<f64>() {
                    if name == "min-width" {
                        min_px = Some(px);
                    } else {
                        max_px = Some(px);
                    }
                }
            }
            _ => {}
        }
    }
    (min_px, max_px)
}

fn media_query(prelude: &str, line: u32) -> LocatedMediaQuery {
    let toks = tokenize(prelude);
    let (min_px, max_px) = feature_widths(prelude, &toks);
    LocatedMediaQuery {
        prelude: prelude.to_owned(),
        min_px,
        max_px,
        line,
    }
}

/// Attach waiver comments to declarations: the first declaration on the comment's line wins,
/// else the nearest declaration whose value starts after the comment, else the waiver is an
/// orphan.
fn attach_waivers(
    comments: Vec<(Waiver, usize)>,
    declarations: &mut [Declaration],
    orphans: &mut Vec<Waiver>,
) {
    for (waiver, offset) in comments {
        if let Some(d) = declarations.iter_mut().find(|d| d.line == waiver.line) {
            d.waivers.push(waiver);
            continue;
        }
        let nearest = declarations
            .iter_mut()
            .filter(|d| d.span.0 > offset)
            .min_by_key(|d| d.span.0);
        match nearest {
            Some(d) => d.waivers.push(waiver),
            None => orphans.push(waiver),
        }
    }
}

/// Parse one CSS file's `source` into its located facts.
///
/// Malformed CSS never fails: syntax errors become [`ParsedCss::errors`] and the rest of the
/// file still parses.
///
/// # Errors
///
/// [`FoldFailure`] when the CSS adapter builds an ill-formed term (an adapter bug).
pub fn parse_css_source(
    entry: &FileEntry,
    source: &str,
    root_font_size: f64,
) -> Result<ParsedCss, FoldFailure> {
    let folded = fold_file(entry, source).map_err(|e| FoldFailure {
        path: entry.path.clone(),
        detail: e.to_string(),
    })?;
    let lines = Lines::of(source);
    let model = Model::new(folded.term, folded.scopes);
    let mut walker = Walker {
        source,
        lines,
        root_font_size,
        model: &model,
        declarations: style::declarations(&model)
            .into_iter()
            .map(|d| (d.node, d))
            .collect(),
        customs: style::custom_properties(&model)
            .into_iter()
            .map(|c| (c.node, c))
            .collect(),
        rules: style::style_rules(&model)
            .into_iter()
            .map(|r| (r.node, r))
            .collect(),
        at_rules: style::at_rules(&model)
            .into_iter()
            .map(|a| (a.node, a))
            .collect(),
        out: ParsedCss::default(),
    };
    let root = model.term().root();
    walker.visit_children(root);
    let Walker { lines, mut out, .. } = walker;

    for id in model.term().ids() {
        if model.term().node(id).op().is_hole() {
            let line = text_range(&model, id).map_or(1, |(s, _)| lines.line_of(s));
            out.errors.push(format!("css syntax error at line {line}"));
        }
    }

    let scan = scanner().scan(Language::Css, source, &folded.file);
    let mut comments = Vec::new();
    for d in &scan.directives {
        if d.namespace != "crunk" || d.verb != "waive" {
            continue;
        }
        let offset = u32::from(d.span.range.start()) as usize;
        match Waive::parse_args(&d.args) {
            Ok(w) => comments.push((
                Waiver {
                    rule: w.rule,
                    reason: w.reason,
                    line: lines.line_of(offset),
                },
                offset,
            )),
            Err(err) => out.errors.push(format!(
                "malformed crunk:waive at line {}: {err}",
                lines.line_of(offset)
            )),
        }
    }
    for f in &scan.findings {
        let line = f
            .span
            .map_or(1, |s| lines.line_of(u32::from(s.range.start()) as usize));
        out.errors
            .push(format!("directive at line {line}: {}", f.message));
    }
    let mut orphans = Vec::new();
    attach_waivers(comments, &mut out.declarations, &mut orphans);
    out.orphan_waivers = orphans;

    tracing::debug!(
        path = %entry.path,
        decls = out.declarations.len(),
        classes = out.class_selectors.len(),
        custom_props = out.custom_props.len(),
        errors = out.errors.len(),
        "ingest: css parsed"
    );
    Ok(out)
}
