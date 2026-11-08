//! Per-node inputs of the solve: taffy style, inherited text, token bindings.

// frob:ticket 01M5XCWYB9M2YSJ5EGABMREX1B

use std::collections::BTreeMap;

use crunk_scene::{ElementKind, SceneDoc, SceneElement};

use super::SolveError;
use super::textstyle::{root_text_style, text_style_for};
use super::tokens::token_bindings;
use crate::style::{ElementRef, StyledNode, StyledScene, TokenMap, inline_decls};
use crate::text::TextStyle;

/// The text a leaf measures and the style it measures under.
#[derive(Debug, Clone)]
pub(crate) struct TextCtx {
    /// The text content (runs joined by a space).
    pub text: String,
    /// The inherited text style.
    pub style: TextStyle,
}

/// Everything the tree builder needs about one layout node.
#[derive(Debug)]
pub(crate) struct Prepared {
    pub data_id: String,
    /// Index (into the prepared list) of the nearest layout ancestor.
    pub parent: Option<usize>,
    pub style: taffy::Style,
    pub hidden: bool,
    pub text: Option<TextCtx>,
    pub tokens: BTreeMap<String, String>,
    /// The tag when it is unknown or a component the solver cannot lay out.
    pub unknown_tag: Option<String>,
}

/// Prepare every styled node, inheriting text styles down the tree.
pub(crate) fn prepare(
    doc: &SceneDoc,
    styled: &StyledScene,
    tokens: &TokenMap,
) -> Result<Vec<Prepared>, SolveError> {
    let by_id: BTreeMap<&str, &SceneElement> = doc
        .elements
        .iter()
        .filter_map(|e| e.data_id.as_deref().map(|id| (id, e)))
        .collect();
    let mut text_styles: Vec<TextStyle> = Vec::with_capacity(styled.nodes.len());
    let mut out = Vec::with_capacity(styled.nodes.len());
    for node in &styled.nodes {
        let el = by_id[node.data_id.as_str()];
        let parent_style = node
            .parent
            .map_or_else(root_text_style, |p| text_styles[p].clone());
        let p = prepare_one(node, el, tokens, &parent_style)?;
        text_styles.push(p.1);
        out.push(p.0);
    }
    tracing::debug!(nodes = out.len(), "solve inputs prepared");
    Ok(out)
}

fn prepare_one(
    node: &StyledNode,
    el: &SceneElement,
    tokens: &TokenMap,
    parent_style: &TextStyle,
) -> Result<(Prepared, TextStyle), SolveError> {
    let attr = el.attributes.iter().find(|(k, _)| k == "style");
    let decls = inline_decls(attr.map(|(_, v)| v.as_str()));
    let eref = ElementRef {
        data_id: &node.data_id,
        line: node.line,
    };
    let style = text_style_for(eref, &decls, tokens, parent_style)?;
    let unknown = el.kind != ElementKind::Html;
    let text = own_text(el).filter(|_| !unknown).map(|text| TextCtx {
        text,
        style: style.clone(),
    });
    let prepared = Prepared {
        data_id: node.data_id.clone(),
        parent: node.parent,
        style: node.style.clone(),
        hidden: node.hidden,
        text,
        tokens: token_bindings(&decls),
        unknown_tag: unknown.then(|| el.tag.clone()),
    };
    Ok((prepared, style))
}

/// The element's direct text runs joined by a space, when non-empty.
fn own_text(el: &SceneElement) -> Option<String> {
    let text = el.text.join(" ");
    (!text.trim().is_empty()).then_some(text)
}
