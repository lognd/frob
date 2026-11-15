//! Scene-level styling: per-element styles from the parsed scene, and the taffy tree keyed by data-id.

// frob:ticket 01M5XCWXYNXW0RW8VRDQPY31M6

use std::collections::BTreeMap;

use crunk_scene::{SceneDoc, SceneRule};
use taffy::{NodeId, Style, TaffyTree};

use super::error::{FindingKind, StyleError, StyleFinding};
use super::map::{ElementRef, ParentCtx, map_declarations};
use super::tokens::TokenMap;

/// Tags that structure the document but never take part in layout.
const NON_RENDER_TAGS: &[&str] = &[
    "html", "head", "body", "style", "script", "title", "meta", "link",
];

/// One layout-participating element with its mapped style.
#[derive(Debug, Clone)]
pub struct StyledNode {
    /// The element's `data-id`.
    pub data_id: String,
    /// 1-based line of its start tag.
    pub line: u32,
    /// Index (into [`StyledScene::nodes`]) of the nearest layout ancestor.
    pub parent: Option<usize>,
    /// The mapped taffy style.
    pub style: Style,
    /// Removed from layout by `display:none` on itself or an ancestor; the id is still reported.
    pub hidden: bool,
    /// The element has direct text (a later text ticket attaches a measure hook).
    pub has_text: bool,
    /// CSS `order`: siblings are laid out by ascending order, ties in document order.
    pub order: i32,
}

/// Every layout node of a scene, in document order (parents before children), plus findings.
#[derive(Debug, Clone, Default)]
pub struct StyledScene {
    /// The nodes.
    pub nodes: Vec<StyledNode>,
    /// Non-fatal findings from every element.
    pub findings: Vec<StyleFinding>,
}

/// Map every element of `doc` to a taffy style, resolving tokens.
///
/// Supported `<style>` rules (see [`SceneDoc::rules`]) apply to the elements they match in source
/// order, then inline `style` attributes override them. Each `<style>` holding anything not
/// applied (an unsupported selector, `@media` or another at-rule) adds a
/// [`FindingKind::StylesheetNotApplied`] finding (the solver refuses on it; see
/// docs/design/crunk/stylesheet-solve.md).
///
/// # Errors
/// Every [`StyleError`] found (one per offending element or declaration), not just the first.
pub fn style_scene(
    doc: &SceneDoc,
    tokens: &TokenMap,
    viewport: ParentCtx,
) -> Result<StyledScene, Vec<StyleError>> {
    let mut out = StyledScene::default();
    let mut errors = Vec::new();
    let mut ctxs: Vec<ParentCtx> = Vec::new();
    let mut anchor: Vec<Option<usize>> = Vec::with_capacity(doc.elements.len());
    let mut seen: BTreeMap<String, u32> = BTreeMap::new();
    for (i, el) in doc.elements.iter().enumerate() {
        let up = el.parent.filter(|p| *p < i).and_then(|p| anchor[p]);
        let line = el.line;
        if el.tag == "style" && stylesheet_has_unapplied(doc, i) {
            tracing::warn!(line, "`<style>` rules found; the solver cannot apply them");
            out.findings.push(StyleFinding {
                kind: FindingKind::StylesheetNotApplied,
                element: String::new(),
                line,
                property: String::new(),
                message: "`<style>` rules and `@media` blocks are not applied by the solver; \
                          move the declarations to inline `style` attributes"
                    .to_owned(),
            });
        }
        let Some(id) = el
            .data_id
            .as_deref()
            .filter(|_| !NON_RENDER_TAGS.contains(&el.tag.as_str()))
        else {
            if !NON_RENDER_TAGS.contains(&el.tag.as_str()) {
                out.findings.push(StyleFinding {
                    kind: FindingKind::MissingDataId,
                    element: el.tag.clone(),
                    line,
                    property: String::new(),
                    message: format!("`<{}>` has no data-id and is left out of layout", el.tag),
                });
            }
            anchor.push(up);
            continue;
        };
        if let Some(first) = seen.insert(id.to_owned(), line) {
            errors.push(StyleError::DuplicateDataId {
                element: id.to_owned(),
                line,
                first_line: first,
            });
            anchor.push(up);
            continue;
        }
        let decls = element_decls(doc, i);
        let parent_ctx = up.map_or(viewport, |p| ctxs[p]);
        match map_declarations(ElementRef { data_id: id, line }, &decls, tokens, parent_ctx) {
            Ok(m) => {
                let parent_hidden = up.is_some_and(|p| out.nodes[p].hidden);
                out.findings.extend(m.findings);
                let idx = out.nodes.len();
                out.nodes.push(StyledNode {
                    data_id: id.to_owned(),
                    line,
                    parent: up,
                    style: m.style,
                    hidden: m.hidden || parent_hidden,
                    has_text: el.text.iter().any(|t| !t.trim().is_empty()),
                    order: m.order,
                });
                ctxs.push(m.child_ctx);
                anchor.push(Some(idx));
            }
            Err(e) => {
                tracing::debug!(element = id, error = %e, "element style failed");
                errors.push(e);
                anchor.push(up);
            }
        }
    }
    if errors.is_empty() {
        tracing::debug!(
            nodes = out.nodes.len(),
            findings = out.findings.len(),
            "scene styled"
        );
        Ok(out)
    } else {
        Err(errors)
    }
}

/// Split an inline `style` attribute into `(property, value)` pairs, skipping custom properties.
fn inline_decls(attr: Option<&str>) -> Vec<(String, String)> {
    let Some(attr) = attr else { return Vec::new() };
    let mut parts = Vec::new();
    let (mut depth, mut start) = (0usize, 0usize);
    for (i, c) in attr.char_indices() {
        match c {
            '(' => depth += 1,
            ')' => depth = depth.saturating_sub(1),
            ';' if depth == 0 => {
                parts.push(&attr[start..i]);
                start = i + 1;
            }
            _ => {}
        }
    }
    parts.push(&attr[start..]);
    parts
        .into_iter()
        .filter_map(|p| p.split_once(':'))
        .map(|(k, v)| (k.trim().to_owned(), v.trim().to_owned()))
        .filter(|(k, _)| !k.is_empty() && !k.starts_with("--"))
        .collect()
}

/// The taffy tree for a styled scene, keyed by data-id.
#[derive(Debug)]
pub struct LayoutTree {
    /// The tree; leaves have no measure hook yet.
    pub tree: TaffyTree<()>,
    /// Layout nodes by data-id (hidden elements are absent).
    pub ids: BTreeMap<String, NodeId>,
    /// Root nodes (no layout ancestor), in document order.
    pub roots: Vec<NodeId>,
    /// data-ids removed from layout by `display:none`, in document order.
    pub hidden: Vec<String>,
}

/// Build the taffy tree from the non-hidden nodes of `scene`.
///
/// # Errors
/// [`StyleError::Engine`] when taffy rejects the tree (an internal inconsistency).
pub fn build_taffy(scene: &StyledScene) -> Result<LayoutTree, StyleError> {
    let engine = |e: taffy::TaffyError| StyleError::Engine(e.to_string());
    let mut tree: TaffyTree<()> = TaffyTree::new();
    let mut ids = BTreeMap::new();
    let mut by_index: BTreeMap<usize, NodeId> = BTreeMap::new();
    let (mut roots, mut hidden) = (Vec::new(), Vec::new());
    let mut kids: BTreeMap<usize, Vec<(i32, NodeId)>> = BTreeMap::new();
    for (i, n) in scene.nodes.iter().enumerate() {
        if n.hidden {
            hidden.push(n.data_id.clone());
            continue;
        }
        let id = tree.new_leaf(n.style.clone()).map_err(engine)?;
        match n.parent.filter(|p| by_index.contains_key(p)) {
            Some(parent) => kids.entry(parent).or_default().push((n.order, id)),
            None => roots.push(id),
        }
        by_index.insert(i, id);
        ids.insert(n.data_id.clone(), id);
    }
    for (parent, mut children) in kids {
        children.sort_by_key(|(order, _)| *order);
        for (_, child) in children {
            tree.add_child(by_index[&parent], child).map_err(engine)?;
        }
    }
    tracing::debug!(
        laid_out = ids.len(),
        hidden = hidden.len(),
        "taffy tree built"
    );
    Ok(LayoutTree {
        tree,
        ids,
        roots,
        hidden,
    })
}

/// The `(property, value)` pairs that style element `idx`: matching supported rules in source
/// order, then its inline `style` attribute (so inline wins).
pub(crate) fn element_decls(doc: &SceneDoc, idx: usize) -> Vec<(String, String)> {
    let mut out: Vec<(String, String)> = Vec::new();
    for rule in applied_rules(doc).filter(|r| r.matches.binary_search(&idx).is_ok()) {
        out.extend(rule_decl_offsets(doc, rule).into_iter().map(|d| {
            (
                doc.declarations[d].property.clone(),
                doc.declarations[d].value.clone(),
            )
        }));
    }
    let inline = doc.elements[idx]
        .attributes
        .iter()
        .find(|(k, _)| k == "style")
        .map(|(_, v)| v.as_str());
    out.extend(inline_decls(inline));
    out
}

/// The rules the solver applies: supported selector, not inside an at-rule.
fn applied_rules(doc: &SceneDoc) -> impl Iterator<Item = &SceneRule> {
    doc.rules
        .iter()
        .filter(|r| r.supported && r.at_rule.is_none())
}

/// Indices into `doc.declarations` of the plain declarations of `rule`: those from its start up to
/// the next rule, at-rule or element start.
fn rule_decl_offsets(doc: &SceneDoc, rule: &SceneRule) -> Vec<usize> {
    let end = doc
        .rules
        .iter()
        .map(|r| r.offset)
        .chain(doc.at_rule_sites.iter().map(|a| a.offset))
        .chain(doc.elements.iter().map(|e| e.offset))
        .filter(|o| *o > rule.offset)
        .min()
        .unwrap_or(usize::MAX);
    doc.declarations
        .iter()
        .enumerate()
        .filter(|(_, d)| d.at_rule.is_none() && d.offset >= rule.offset && d.offset < end)
        .map(|(i, _)| i)
        .collect()
}

/// Whether the `<style>` element at `idx` holds anything the solver does not apply: an at-rule, or
/// a declaration outside every applied rule (an unsupported selector's body, a bare declaration).
fn stylesheet_has_unapplied(doc: &SceneDoc, idx: usize) -> bool {
    let start = doc.elements[idx].offset;
    let end = doc
        .elements
        .iter()
        .map(|e| e.offset)
        .filter(|o| *o > start)
        .min()
        .unwrap_or(usize::MAX);
    let inside = |o: usize| o > start && o < end;
    if doc.at_rule_sites.iter().any(|a| inside(a.offset)) {
        return true;
    }
    let applied: std::collections::BTreeSet<usize> = applied_rules(doc)
        .flat_map(|r| rule_decl_offsets(doc, r))
        .collect();
    doc.declarations
        .iter()
        .enumerate()
        .any(|(i, d)| inside(d.offset) && !applied.contains(&i))
}
