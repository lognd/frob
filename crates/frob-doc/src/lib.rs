//! `frob doc remap`: the `docs/MOVED.toml` relocation map and the rewrite of every reference that
//! still points at an old doc place.
//!
//! [`MovedMap`] parses and follows the map (the one format DOC006, DOC002, DRIFT002 and the remap
//! share); [`remap`] turns a map plus a repository into a validated [`Plan`] of text edits.

// frob:ticket 01M4H0WXVXJ18DX9SVX6EHT0AD

mod edit;
mod moved;
mod plan;
mod rewrite;

pub use moved::{Kind, MAX_HOPS, MOVED_PATH, MovedError, MovedMap, Ref, Resolved, Row};
pub use plan::{FileChange, Plan, RemapError, RowProblem, remap};
pub use rewrite::{in_scope, remap_text};
