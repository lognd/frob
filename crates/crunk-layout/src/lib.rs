//! crunk's layout-side graphs over parsed scenes (docs/design/crunk.md section 7). Today that is
//! the gamepad focus graph: [`FocusGraph::from_scene`] derives it from a scene's markup without the
//! layout solver or the editor, so the GX checks run at T0.

// frob:ticket 01M4CXRSYQQW9C6D7K2Q2ZC9QM

mod focus;
pub mod style;

pub use focus::{
    Direction, FocusEdge, FocusGraph, FocusNode, GroupAxis, InvalidEdge, InvalidReason, WrapMode,
};
