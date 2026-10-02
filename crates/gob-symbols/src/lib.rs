//! Symrefs, three-facet digests, imports and call graph (D31, code-model
//! sections 2 and 3).
//!
//! # Overview
//!
//! - [`Symref`]: parsed `path`, `path::Qual.Name` and `path#slug` addresses.
//! - [`SymbolRecord`] with [`Digests`] (`sig`, `body`, `doc`; blake3 over
//!   whitespace-collapsed facet text).
//! - [`extract_file`]: one file to a [`FileSymbols`] (symbols, imports and
//!   call sites) for Rust and markdown.
//! - [`SymbolGraph`]: petgraph nodes per symbol (plus one node per file)
//!   with Contains, Imports and Calls edges; [`SymbolGraph::public_api`],
//!   [`SymbolGraph::affects`], [`SymbolGraph::reach`],
//!   [`SymbolGraph::graph_digest`] and [`SymbolGraph::resolve`].
//! - [`build_graph`]: parallel (rayon) and incremental (per-file artifacts in
//!   [`gob_cache::Cache`]) pipeline.
//!
//! # Conventions
//!
//! - Files are symbols too: the whole-file symref `path` is a
//!   [`SymbolKind::Module`] node that contains the file's top-level items.
//! - An impl block is `Type[Trait]` (or `Type[impl]`); its members are
//!   `Type.method`, becoming `Type[Trait].method` only on a collision.
//! - Cached payloads are serialized with `postcard` (compact, stable wire
//!   format, serde-derived) under the producer identity
//!   `gob-symbols/v<EXTRACTOR_VERSION>/<grammar identity>`.

mod graph;
mod markdown;
mod model;
mod paths;
mod pipeline;
mod rust;
mod symref;

pub use graph::{CallEdge, EdgeKind, ResolveError, SymbolGraph};
pub use markdown::slugify;
pub use model::{
    CallSite, Digests, FacetDigest, FileSymbols, ImportEdge, SymbolKind, SymbolRecord, Visibility,
    collapse_ws,
};
pub use pipeline::{
    BuildStats, EXTRACTOR_VERSION, build_graph, build_graph_with_stats, extract_file,
};
pub use symref::{Symref, SymrefError, Target};
