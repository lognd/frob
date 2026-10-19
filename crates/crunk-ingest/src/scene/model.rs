//! The scene description: serde model and its parser.

// frob:ticket 01M4S9HRETE0RW4H034W1H7QCD

use serde::{Deserialize, Serialize};

/// Why a scene could not be parsed or solved.
#[derive(Debug, thiserror::Error)]
pub enum SceneError {
    /// The scene text is not valid scene JSON.
    #[error("scene is not valid JSON: {0}")]
    Parse(#[from] serde_json::Error),
    /// A dimension is neither a number, `auto`, nor `N%`.
    #[error("node {id}: invalid dimension {value:?} (want a number, \"auto\" or \"N%\")")]
    BadDimension {
        /// The node carrying the dimension.
        id: String,
        /// The offending text.
        value: String,
    },
    /// The layout engine rejected the tree.
    #[error("layout engine failed: {0}")]
    Engine(String),
}

/// The viewport the scene is solved against, in pixels.
#[derive(Debug, Clone, Copy, PartialEq, Deserialize, Serialize)]
pub struct Viewport {
    /// Viewport width.
    pub width: f32,
    /// Viewport height.
    pub height: f32,
}

/// A length: a number of pixels, `"auto"` or a percentage such as `"50%"`.
#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
#[serde(untagged)]
pub enum Dim {
    /// Pixels.
    Px(f32),
    /// `"auto"` or `"N%"`.
    Text(String),
}

/// What a node is.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum NodeKind {
    /// A container or leaf rectangle.
    Box,
    /// A run of text sized by the deterministic metrics.
    Text,
}

/// The layout style subset a scene node may carry.
#[derive(Debug, Clone, Default, PartialEq, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
pub struct SceneStyle {
    /// `flex` (default), `block` or `none`.
    pub display: Option<String>,
    /// `row` (default) or `column`.
    pub direction: Option<String>,
    /// Whether flex items wrap.
    pub wrap: bool,
    /// Gap between flex items, pixels.
    pub gap: f32,
    /// Padding on all sides, pixels.
    pub padding: f32,
    /// Margin on all sides, pixels.
    pub margin: f32,
    /// Width.
    pub width: Option<Dim>,
    /// Height.
    pub height: Option<Dim>,
    /// Flex grow factor.
    pub grow: f32,
    /// Flex shrink factor (default 1).
    pub shrink: Option<f32>,
}

/// A text run's content and metrics inputs.
#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct TextRun {
    /// The text.
    pub content: String,
    /// Font size, pixels.
    pub font_size: f32,
    /// Line height as a multiple of the font size (default 1.2).
    #[serde(default)]
    pub line_height: Option<f32>,
    /// Wrap width, pixels; `None` keeps one line per `\n`.
    #[serde(default)]
    pub max_width: Option<f32>,
}

/// One node of the scene tree.
#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct SceneNode {
    /// Stable id, unique within the scene.
    pub id: String,
    /// `box` or `text`.
    pub kind: NodeKind,
    /// Layout style.
    #[serde(default)]
    pub style: SceneStyle,
    /// The text, for a `text` node.
    #[serde(default)]
    pub text: Option<TextRun>,
    /// Whether the node is a pointer or touch target (button, link, control); LAYOUT005 sizes it.
    #[serde(default)]
    pub interactive: bool,
    /// Child nodes.
    #[serde(default)]
    pub children: Vec<SceneNode>,
}

/// A parsed scene: a viewport and its root node.
#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct Scene {
    /// The viewport to solve against.
    pub viewport: Viewport,
    /// Inset from every viewport edge that text and targets must stay inside (notches, home
    /// indicators), pixels; 0 (default) means no safe-area constraint.
    #[serde(default)]
    pub safe_area: f32,
    /// The root node.
    pub root: SceneNode,
}

/// Parse scene JSON into a [`Scene`].
///
/// # Errors
///
/// Returns [`SceneError::Parse`] if the text is not valid scene JSON.
pub fn parse_scene(text: &str) -> Result<Scene, SceneError> {
    let scene: Scene = serde_json::from_str(text)?;
    tracing::debug!(root = %scene.root.id, "scene parsed");
    Ok(scene)
}
