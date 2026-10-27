//! Solver style mapping: resolved scene CSS to taffy styles (D111, D113).
//!
//! # Input and output
//! [`style_scene`] reads a parsed scene plus a [`TokenMap`] and maps each element's inline
//! `style` attribute to a taffy [`taffy::Style`]; [`build_taffy`] then builds a
//! [`taffy::TaffyTree`] keyed by data-id. There is no text measurement here: nodes with text
//! (`StyledNode::has_text`) get a measure hook from the text ticket. `<style>` rules and
//! `@media` are not applied yet (the scene parser does not tie rules to elements).
//!
//! # Supported properties
//! `display` (block, flex, grid, none), `position` (static, relative, absolute), `top/right/
//! bottom/left/inset`, `width/height`, `min-*`, `max-*`, `margin`, `padding`, `border` widths,
//! `gap/row-gap/column-gap`, `flex-direction/wrap/flow/flex/grow/shrink/basis`, `align-*`,
//! `justify-*`, `aspect-ratio`, `box-sizing`, `grid-template-columns/rows` (px, %, fr, auto,
//! min/max-content, `minmax()`, `repeat()`), `grid-auto-*`, `grid-column/row` (lines, spans).
//! Units: `px`, `rem` (16px), `%`, unitless `0`. Properties not mapped yet
//! (`grid-template-areas`, `grid-area`, `order`, `place-*`) yield an `UnmappedProperty` finding;
//! paint and text properties are ignored.
//!
//! # Rules
//! - `box-sizing` defaults to content-box (the CSS initial value), `display` to block.
//! - `var(--x, fallback)` resolves recursively; an undefined token without a fallback is
//!   [`StyleError::UndefinedToken`] naming the element and line.
//! - `display:none` keeps the data-id in [`LayoutTree::hidden`] and out of the tree, with its
//!   descendants.
//! - Negative padding, gap or border width clamps to 0 and negative sizes become auto, each as a
//!   `NegativeValue` finding. `min-*` above `max-*` raises the max to the min.
//! - A percentage size is auto when the parent axis is indefinite. The width axis is definite
//!   when the parent has a length or definite percentage width, or an auto width in flow under a
//!   definite grandparent; the height axis only for a length or definite percentage height.
//! - `aspect-ratio` is ignored when both width and height are set.
//! - Grid spans are not clamped, so spans past the explicit tracks create implicit tracks.
//! - Opposing absolute insets with no size keep size auto, which taffy stretches.

// frob:ticket 01M5XCWXYNXW0RW8VRDQPY31M6

mod error;
mod map;
mod tokens;
mod tree;
mod value;

pub use error::{FindingKind, StyleError, StyleFinding};
pub use map::{ElementRef, MappedStyle, ParentCtx, map_declarations};
pub use tokens::TokenMap;
pub use tree::{LayoutTree, StyledNode, StyledScene, build_taffy, style_scene};
