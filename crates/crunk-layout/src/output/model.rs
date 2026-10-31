//! Layout-solve model types, normalization (grid snap, zero-size, overflow) and serialization.

// frob:ticket 01M5XCWY267M72G3GPYE2ZAPQ5

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use super::error::OutputError;
use crate::FocusGraph;

/// The shipped JSON Schema of the layout-solve document.
pub const SCHEMA_V1: &str = include_str!("../../../../docs/schemas/crunk-layout-solve-v1.json");

/// Coordinates snap to multiples of `1 / GRID` pixels.
pub const GRID: f32 = 64.0;

/// What a node is (same wire form as the scene mini-solver).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum NodeKind {
    /// A container or leaf rectangle.
    Box,
    /// A run of text.
    Text,
}

/// An axis of overflow.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Axis {
    /// Horizontal.
    X,
    /// Vertical.
    Y,
}

/// Content spilling out of a node's box along one axis.
#[derive(Debug, Clone, Copy, PartialEq, Deserialize, Serialize)]
pub struct Overflow {
    /// Which axis overflows.
    pub axis: Axis,
    /// By how many pixels (grid-snapped, always positive).
    pub amount: f32,
}

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

/// One node of the layout-solve document, as written.
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
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub text: Option<SolvedText>,
    /// True when the width or the height is zero.
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub zero_size: bool,
    /// Axes along which content overflows the box (x before y); absent when none does.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub overflow: Vec<Overflow>,
    /// Computed token bindings: property name to token name, sorted by property.
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub tokens: BTreeMap<String, String>,
}

/// The layout-solve document (`crunk-layout-solve-v1.json`).
#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct LayoutSolve {
    /// Schema version, always 1.
    pub version: u32,
    /// Viewport width.
    pub viewport_width: f32,
    /// Viewport height.
    pub viewport_height: f32,
    /// Solved nodes in document (preorder) order.
    pub nodes: Vec<SolvedNode>,
    /// `data-id`s of the focusable nodes in tab order.
    pub focus_order: Vec<String>,
}

/// A node as the solver produced it, before normalization.
#[derive(Debug, Clone, PartialEq)]
pub struct RawNode {
    /// The scene id.
    pub id: String,
    /// The parent's id; `None` for the root.
    pub parent: Option<String>,
    /// `box` or `text`.
    pub kind: NodeKind,
    /// Left edge.
    pub x: f32,
    /// Top edge.
    pub y: f32,
    /// Width.
    pub width: f32,
    /// Height.
    pub height: f32,
    /// Extent of the node's content horizontally, when known.
    pub content_width: Option<f32>,
    /// Extent of the node's content vertically, when known.
    pub content_height: Option<f32>,
    /// Text metrics, for a `text` node.
    pub text: Option<SolvedText>,
    /// Computed token bindings.
    pub tokens: BTreeMap<String, String>,
}

/// A whole solve as the solver produced it, before normalization.
#[derive(Debug, Clone, PartialEq)]
pub struct RawSolve {
    /// Viewport width.
    pub viewport_width: f32,
    /// Viewport height.
    pub viewport_height: f32,
    /// Nodes in document order.
    pub nodes: Vec<RawNode>,
    /// Focusable `data-id`s in tab order.
    pub focus_order: Vec<String>,
}

/// Snap `value` to the 1/64 px grid; `-0.0` becomes `0.0`. `None` when `value` is NaN or
/// infinite, or leaves the finite range once scaled.
pub fn snap(value: f32) -> Option<f32> {
    let scaled = (value * GRID).round();
    if !scaled.is_finite() {
        return None;
    }
    let snapped = scaled / GRID;
    Some(if snapped == 0.0 { 0.0 } else { snapped })
}

/// Tab order for the document: the `data-id`s of the graph's focusable nodes, document order.
/// Focusables without a `data-id` cannot be named in the document and are skipped.
pub fn focus_order(graph: &FocusGraph) -> Vec<String> {
    graph
        .nodes
        .iter()
        .filter_map(|n| n.data_id.clone())
        .collect()
}

fn snap_field(
    value: f32,
    owner: impl Fn() -> String,
    field: &'static str,
) -> Result<f32, OutputError> {
    snap(value).ok_or_else(|| {
        let owner = owner();
        tracing::warn!(%owner, field, "non-finite layout value");
        OutputError::NonFinite { owner, field }
    })
}

fn overflow_of(
    axis: Axis,
    content: Option<f32>,
    size: f32,
    owner: &str,
) -> Result<Option<Overflow>, OutputError> {
    let Some(content) = content else {
        return Ok(None);
    };
    let field = match axis {
        Axis::X => "content_width",
        Axis::Y => "content_height",
    };
    let content = snap_field(content, || owner.to_owned(), field)?;
    let amount = snap_field(content - size, || owner.to_owned(), field)?;
    Ok((amount > 0.0).then_some(Overflow { axis, amount }))
}

impl RawNode {
    fn normalize(self) -> Result<SolvedNode, OutputError> {
        let owner = format!("node '{}'", self.id);
        let o = || owner.clone();
        let x = snap_field(self.x, o, "x")?;
        let y = snap_field(self.y, o, "y")?;
        let width = snap_field(self.width, o, "width")?;
        let height = snap_field(self.height, o, "height")?;
        let overflow = [
            overflow_of(Axis::X, self.content_width, width, &owner)?,
            overflow_of(Axis::Y, self.content_height, height, &owner)?,
        ]
        .into_iter()
        .flatten()
        .collect();
        let text = match self.text {
            Some(mut t) => {
                t.font_size = snap_field(t.font_size, o, "font_size")?;
                Some(t)
            }
            None => None,
        };
        Ok(SolvedNode {
            zero_size: width == 0.0 || height == 0.0,
            id: self.id,
            parent: self.parent,
            kind: self.kind,
            x,
            y,
            width,
            height,
            text,
            overflow,
            tokens: self.tokens,
        })
    }
}

impl RawSolve {
    /// Normalize into the document: snap to the grid, flag zero-size nodes, record overflow.
    ///
    /// # Errors
    ///
    /// [`OutputError::NonFinite`] naming the first NaN or infinite value found.
    pub fn finish(self) -> Result<LayoutSolve, OutputError> {
        let viewport = || "viewport".to_owned();
        let viewport_width = snap_field(self.viewport_width, viewport, "viewport_width")?;
        let viewport_height = snap_field(self.viewport_height, viewport, "viewport_height")?;
        let nodes = self
            .nodes
            .into_iter()
            .map(RawNode::normalize)
            .collect::<Result<Vec<_>, _>>()?;
        tracing::debug!(nodes = nodes.len(), "layout solve normalized");
        Ok(LayoutSolve {
            version: 1,
            viewport_width,
            viewport_height,
            nodes,
            focus_order: self.focus_order,
        })
    }
}

impl LayoutSolve {
    /// Pretty JSON with a trailing newline; byte-identical for equal documents.
    ///
    /// Values are re-snapped first, so a hand-edited document cannot leak `-0.0` or off-grid
    /// numbers.
    ///
    /// # Errors
    ///
    /// [`OutputError::NonFinite`] when a field is NaN or infinite, [`OutputError::Serialize`]
    /// otherwise.
    pub fn to_json(&self) -> Result<String, OutputError> {
        let raw = RawSolve {
            viewport_width: self.viewport_width,
            viewport_height: self.viewport_height,
            nodes: self
                .nodes
                .iter()
                .map(|n| RawNode {
                    id: n.id.clone(),
                    parent: n.parent.clone(),
                    kind: n.kind,
                    x: n.x,
                    y: n.y,
                    width: n.width,
                    height: n.height,
                    content_width: None,
                    content_height: None,
                    text: n.text.clone(),
                    tokens: n.tokens.clone(),
                })
                .collect(),
            focus_order: self.focus_order.clone(),
        };
        let mut clean = raw.finish()?;
        for (c, n) in clean.nodes.iter_mut().zip(&self.nodes) {
            c.overflow = n
                .overflow
                .iter()
                .map(|o| {
                    snap_field(o.amount, || format!("node '{}'", n.id), "overflow").map(|amount| {
                        Overflow {
                            axis: o.axis,
                            amount,
                        }
                    })
                })
                .collect::<Result<_, _>>()?;
        }
        let mut out = serde_json::to_string_pretty(&clean)?;
        out.push('\n');
        tracing::debug!(bytes = out.len(), "layout solve serialized");
        Ok(out)
    }
}
