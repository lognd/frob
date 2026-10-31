//! The layout-solve JSON (docs/design/crunk.md section 3): boxes, text runs, overflow, focus
//! order and computed token bindings, serialized deterministically (`crunk-layout-solve-v1.json`).
//!
//! The document is a superset of `crunk_ingest::scene::LayoutSolve`: the same
//! `viewport_width`, `viewport_height` and `nodes` fields with the same node fields, plus
//! `version`, `focus_order` and the per-node `zero_size`, `overflow` and `tokens` fields, so older
//! consumers keep reading it.

// frob:ticket 01M5XCWY267M72G3GPYE2ZAPQ5

mod error;
mod model;

pub use error::OutputError;
pub use model::{
    Axis, GRID, LayoutSolve, NodeKind, Overflow, RawNode, RawSolve, SCHEMA_V1, SolvedNode,
    SolvedText, focus_order, snap,
};
