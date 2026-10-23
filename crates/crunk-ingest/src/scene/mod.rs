//! Scene ingest for crunk: a JSON scene description of boxes and text runs, solved with taffy
//! into a deterministic layout-solve JSON the LAYOUT and RESP rules read.
//!
//! The scene is a tree of `box` and `text` nodes under a `viewport`. [`parse_scene`] reads it,
//! [`solve_scene`] lays it out (flexbox and block, pixel units, rounded to whole pixels) and
//! [`LayoutSolve`] serializes the absolute rectangle of every node in document order. Text
//! has no font engine: a run measures `chars * font_size * 0.6` wide per line and
//! `font_size * line_height` tall per line, wrapping at its optional `max_width`, so the
//! solve is identical on every machine.

// frob:ticket 01M4S9HRETE0RW4H034W1H7QCD

mod docs;
mod model;
mod solve;

pub use docs::{
    LoadedSceneDoc, SCENE_DOC_SUFFIX, SceneDocLoad, SceneDocProblem, SceneDocProblemKind,
    is_scene_doc_path, load_scene_docs,
};
pub use model::{
    Dim, NodeKind, Scene, SceneError, SceneNode, SceneStyle, TextRun, Viewport, parse_scene,
};
pub use solve::{LayoutSolve, SolvedNode, SolvedText, solve_scene};
