//! The taffy solve: scene to absolute rectangles.

// frob:ticket 01M4S9HRETE0RW4H034W1H7QCD

use serde::{Deserialize, Serialize};
use taffy::prelude::*;

use super::model::{Dim, NodeKind, Scene, SceneError, SceneNode, SceneStyle, TextRun};

/// Width of one character as a multiple of the font size.
const CHAR_WIDTH_EM: f32 = 0.6;
/// Default line height as a multiple of the font size.
const DEFAULT_LINE_HEIGHT: f32 = 1.2;

/// A text run's solved metrics.
#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct SolvedText {
    /// The text.
    pub content: String,
    /// Font size, pixels.
    pub font_size: f32,
    /// Number of lines after wrapping.
    pub lines: usize,
}

/// One node's solved absolute rectangle.
#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct SolvedNode {
    /// The scene id.
    pub id: String,
    /// The parent's id; `None` for the root.
    pub parent: Option<String>,
    /// `box` or `text`.
    pub kind: NodeKind,
    /// Left edge in viewport coordinates.
    pub x: f32,
    /// Top edge in viewport coordinates.
    pub y: f32,
    /// Width.
    pub width: f32,
    /// Height.
    pub height: f32,
    /// Text metrics, for a `text` node.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub text: Option<SolvedText>,
}

/// The layout-solve document: the viewport and every node in document order.
#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct LayoutSolve {
    /// Viewport width.
    pub viewport_width: f32,
    /// Viewport height.
    pub viewport_height: f32,
    /// Solved nodes, preorder.
    pub nodes: Vec<SolvedNode>,
}

impl LayoutSolve {
    /// Serialize as pretty JSON with a trailing newline; stable across runs.
    ///
    /// # Errors
    ///
    /// Returns [`SceneError::Parse`] if serialization fails.
    pub fn to_json(&self) -> Result<String, SceneError> {
        let mut out = serde_json::to_string_pretty(self)?;
        out.push('\n');
        Ok(out)
    }
}

fn dimension(id: &str, dim: Option<&Dim>) -> Result<Dimension, SceneError> {
    match dim {
        None => Ok(Dimension::auto()),
        Some(Dim::Px(px)) => Ok(Dimension::length(*px)),
        Some(Dim::Text(text)) => {
            let bad = || SceneError::BadDimension {
                id: id.to_owned(),
                value: text.clone(),
            };
            if text == "auto" {
                return Ok(Dimension::auto());
            }
            let pct: f32 = text
                .strip_suffix('%')
                .ok_or_else(bad)?
                .trim()
                .parse()
                .map_err(|_| bad())?;
            Ok(Dimension::percent(pct / 100.0))
        }
    }
}

#[expect(
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    clippy::cast_precision_loss,
    reason = "text lengths are small; metrics are deliberately approximate"
)]
/// Measure a run: (width, height, line count) under the deterministic metrics.
fn measure(run: &TextRun) -> (f32, f32, usize) {
    let char_w = run.font_size * CHAR_WIDTH_EM;
    let per_line = run
        .max_width
        .map(|w| ((w / char_w).floor() as usize).max(1));
    let mut lines = 0usize;
    let mut widest = 0usize;
    for raw in run.content.split('\n') {
        let len = raw.chars().count();
        match per_line {
            Some(cap) if len > cap => {
                lines += len.div_ceil(cap);
                widest = widest.max(cap);
            }
            _ => {
                lines += 1;
                widest = widest.max(len);
            }
        }
    }
    let line_h = run.font_size * run.line_height.unwrap_or(DEFAULT_LINE_HEIGHT);
    (widest as f32 * char_w, lines as f32 * line_h, lines)
}

fn style_of(node: &SceneNode) -> Result<Style, SceneError> {
    let s: &SceneStyle = &node.style;
    let mut size = Size {
        width: dimension(&node.id, s.width.as_ref())?,
        height: dimension(&node.id, s.height.as_ref())?,
    };
    if let (NodeKind::Text, Some(run)) = (node.kind, node.text.as_ref()) {
        let (w, h, _) = measure(run);
        if s.width.is_none() {
            size.width = Dimension::length(w);
        }
        if s.height.is_none() {
            size.height = Dimension::length(h);
        }
    }
    let display = match s.display.as_deref() {
        Some("block") => Display::Block,
        Some("none") => Display::None,
        _ => Display::Flex,
    };
    Ok(Style {
        display,
        flex_direction: match s.direction.as_deref() {
            Some("column") => FlexDirection::Column,
            _ => FlexDirection::Row,
        },
        flex_wrap: if s.wrap {
            FlexWrap::Wrap
        } else {
            FlexWrap::NoWrap
        },
        gap: Size {
            width: LengthPercentage::length(s.gap),
            height: LengthPercentage::length(s.gap),
        },
        padding: Rect {
            left: LengthPercentage::length(s.padding),
            right: LengthPercentage::length(s.padding),
            top: LengthPercentage::length(s.padding),
            bottom: LengthPercentage::length(s.padding),
        },
        margin: Rect {
            left: LengthPercentageAuto::length(s.margin),
            right: LengthPercentageAuto::length(s.margin),
            top: LengthPercentageAuto::length(s.margin),
            bottom: LengthPercentageAuto::length(s.margin),
        },
        size,
        flex_grow: s.grow,
        flex_shrink: s.shrink.unwrap_or(1.0),
        ..Style::default()
    })
}

fn build(
    tree: &mut TaffyTree<()>,
    node: &SceneNode,
    out: &mut Vec<(NodeId, usize)>,
) -> Result<NodeId, SceneError> {
    let engine = |e: taffy::TaffyError| SceneError::Engine(e.to_string());
    let slot = out.len();
    let placeholder = tree.new_leaf(Style::default()).map_err(engine)?;
    out.push((placeholder, slot));
    let mut kids = Vec::with_capacity(node.children.len());
    for child in &node.children {
        kids.push(build(tree, child, out)?);
    }
    let id = tree
        .new_with_children(style_of(node)?, &kids)
        .map_err(engine)?;
    out[slot].0 = id;
    Ok(id)
}

fn collect(
    tree: &TaffyTree<()>,
    node: &SceneNode,
    ids: &mut std::slice::Iter<'_, (NodeId, usize)>,
    origin: (f32, f32),
    parent: Option<&str>,
    out: &mut Vec<SolvedNode>,
) -> Result<(), SceneError> {
    let (nid, _) = ids.next().expect("one taffy id per scene node");
    let l = tree
        .layout(*nid)
        .map_err(|e| SceneError::Engine(e.to_string()))?;
    let (x, y) = (origin.0 + l.location.x, origin.1 + l.location.y);
    out.push(SolvedNode {
        id: node.id.clone(),
        parent: parent.map(str::to_owned),
        kind: node.kind,
        x,
        y,
        width: l.size.width,
        height: l.size.height,
        text: node
            .text
            .as_ref()
            .filter(|_| node.kind == NodeKind::Text)
            .map(|run| SolvedText {
                content: run.content.clone(),
                font_size: run.font_size,
                lines: measure(run).2,
            }),
    });
    for child in &node.children {
        collect(tree, child, ids, (x, y), Some(&node.id), out)?;
    }
    Ok(())
}

/// Lay the scene out against its viewport and return every node's absolute rectangle.
///
/// # Errors
///
/// Returns [`SceneError::BadDimension`] for an unparsable length and [`SceneError::Engine`]
/// if taffy rejects the tree.
pub fn solve_scene(scene: &Scene) -> Result<LayoutSolve, SceneError> {
    let mut tree: TaffyTree<()> = TaffyTree::new();
    let mut ids = Vec::new();
    let root = build(&mut tree, &scene.root, &mut ids)?;
    // build() pushes in preorder, matching collect()'s traversal.
    let available = Size {
        width: AvailableSpace::Definite(scene.viewport.width),
        height: AvailableSpace::Definite(scene.viewport.height),
    };
    tree.compute_layout(root, available)
        .map_err(|e| SceneError::Engine(e.to_string()))?;
    let mut nodes = Vec::with_capacity(ids.len());
    collect(
        &tree,
        &scene.root,
        &mut ids.iter(),
        (0.0, 0.0),
        None,
        &mut nodes,
    )?;
    tracing::info!(nodes = nodes.len(), "scene solved");
    Ok(LayoutSolve {
        viewport_width: scene.viewport.width,
        viewport_height: scene.viewport.height,
        nodes,
    })
}
