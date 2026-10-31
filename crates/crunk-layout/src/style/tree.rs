//! Scene-level styling: per-element styles from the parsed scene, and the taffy tree keyed by data-id.

// frob:ticket 01M5XCWXYNXW0RW8VRDQPY31M6

use std::collections::BTreeMap;

use crunk_scene::SceneDoc;
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
/// Only inline `style` attributes are mapped; `@media` and `<style>` rules are not applied.
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
        if el.tag == "style" {
            out.findings.push(StyleFinding {
                kind: FindingKind::StylesheetNotApplied,
                element: String::new(),
                line,
                property: String::new(),
                message: "`<style>` rules are not applied; only inline style attributes are mapped"
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
        let decls = inline_decls(
            el.attributes
                .iter()
                .find(|(k, _)| k == "style")
                .map(|(_, v)| v.as_str()),
        );
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
    for (i, n) in scene.nodes.iter().enumerate() {
        if n.hidden {
            hidden.push(n.data_id.clone());
            continue;
        }
        let id = tree.new_leaf(n.style.clone()).map_err(engine)?;
        match n.parent.and_then(|p| by_index.get(&p)) {
            Some(parent) => tree.add_child(*parent, id).map_err(engine)?,
            None => roots.push(id),
        }
        by_index.insert(i, id);
        ids.insert(n.data_id.clone(), id);
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
