//! Adapters that fold files into U terms (gob-ir), and the symbol views, imports
//! and call graph computed from them (D31, D56, code-model sections 2 and 3,
//! universal-model.md sections 3, 7 and 8).
//!
//! # Overview
//!
//! - [`Adapter`]: the contract `parse`, `fold`, `capabilities`, `fidelity`.
//!   [`RustAdapter`] (F3), [`PythonAdapter`] (F2), [`MarkdownAdapter`] (F4) and [`OpaqueAdapter`] (F0, for
//!   every file with no adapter) each produce a [`gob_ir::Term`] and a
//!   [`gob_ir::ScopeGraph`] ([`Folded`]); [`adapters`] lists them and the `inventory`-based registry
//!   ([`AdapterEntry`]) lets crates that depend on this one add more.
//! - [`SymbolRecord`] with [`Digests`] (`sig`, `body`, `doc`, `attr`, `contract`):
//!   the `unit` view of a term; digests are gob-ir scheme 2, BLAKE3 over the
//!   canonical facet stream (trivia excluded, outer attributes in Sig, G7-G9).
//! - [`extract_file`]: one file to a [`FileSymbols`] (symbols, imports, call sites,
//!   value references, `use` bindings, parse status and fidelity); [`fold_file`]
//!   also returns the term and scope graph.
//! - [`SymbolGraph`]: petgraph nodes per symbol (plus one node per file) with
//!   Contains, Imports, Calls, References and Links edges, each with a
//!   [`Status`]; [`SymbolGraph::public_api`] (re-exports followed, G10),
//!   [`SymbolGraph::affects`], [`SymbolGraph::reach`],
//!   [`SymbolGraph::affects_with_status`], [`SymbolGraph::reach_with_status`]
//!   (unresolved calls poison reach, G1-G3), [`SymbolGraph::edges_with_status`],
//!   [`SymbolGraph::graph_digest`] and [`SymbolGraph::resolve`].
//! - [`build_graph`]: parallel (rayon) and incremental (per-file artifacts in
//!   [`gob_cache::Cache`]) pipeline.
//!
//! # Conventions
//!
//! - Files are symbols too: the whole-file symref `path` is a
//!   [`SymbolKind::Module`] node that contains the file's top-level items; a file
//!   no adapter claims is that node alone, folded as one `opaque(no-adapter)` unit
//!   at F0 with `parse_status` `NotParsed` (G19).
//! - An impl block is `Type[Trait]` (or `Type[impl]`); its members are
//!   `Type.method`, becoming `Type[Trait].method` only on a collision (the term
//!   itself spells members `Type[Trait].method`; the view compresses).
//! - A call edge is Must for a unique same-crate free function (or an inherent
//!   associated function named through its type), May for methods, trait
//!   dispatch, globs, ambiguous names and calls inside macros, Unknown for an
//!   unresolved or dynamic callee. A function used as a value is a May
//!   reference edge (G4).
//! - Cached payloads are serialized with `postcard` (compact, stable wire
//!   format, serde-derived) under the adapter identity
//!   `gob-symbols/v<EXTRACTOR_VERSION>/<grammar identity>`. Terms are not
//!   cached until gob-ir is serializable; a miss re-folds from source.

mod adapter;
mod crates;
mod fold;
mod graph;
mod markdown;
mod model;
mod opaque;
mod paths;
mod pipeline;
mod python;
mod qualifier;
mod registry;
mod rust;
mod stdtypes;
mod symref;
mod view;
mod yaml;

pub use adapter::{
    Adapter, Capability, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded,
    ParseStatus, Precision,
};
pub use crates::CrateDeps;
/// The facet digest scheme these digests are computed under (recorded in every lock file).
pub use gob_ir::DIGEST_SCHEME;
pub use graph::{
    CallEdge, EdgeKind, FileInfo, GapReason, ReachSet, ResolveError, Status, StatusEdge,
    SymbolGraph,
};
pub use markdown::{MarkdownAdapter, slugify};
pub use model::{
    CallRef, CallSite, DeriveDecl, Digests, FacetDigest, FieldDecl, FileSymbols, ImportEdge,
    LocalBinding, MapKind, MethodSig, Receiver, RefKind, RefSite, RetType, SelfKind, SymbolKind,
    SymbolRecord, UnitExtras, UseBinding, Visibility, collapse_ws,
};
pub use opaque::OpaqueAdapter;
pub use pipeline::{
    BuildStats, EXTRACTOR_VERSION, SkipKind, SkippedFile, build_graph, build_graph_with_stats,
    extract_file, fold_file,
};
pub use python::{
    PythonAdapter, is_python_path, is_python_test_file, is_python_test_fn, is_python_test_module,
};
pub use qualifier::{Admit, CallQualifier};
pub use registry::{
    AdapterEntry, AdapterReport, DuplicateExtension, adapter_for, adapter_for_path, adapters,
    fidelity_report, opaque_adapter, registry_conflicts,
};
pub use rust::RustAdapter;
pub use symref::{Symref, SymrefError, Target};
pub use view::model_symbols;
