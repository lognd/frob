//! Adapters that fold files into U terms (gob-ir), and the symbol views, imports
//! and call graph computed from them (D31, D56, code-model sections 2 and 3,
//! universal-model.md sections 3, 7 and 8).
//!
//! # Overview
//!
//! - [`Adapter`]: the contract `parse`, `fold`, `capabilities`, `fidelity`.
//!   [`RustAdapter`] (F4), [`PythonAdapter`] (F3), [`CSharpAdapter`] (F1), [`TypeScriptAdapter`] (F3), [`CssAdapter`] (F2), [`HtmlAdapter`] (F0), [`MarkdownAdapter`] (F3) and [`OpaqueAdapter`] (F0, for
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
//! - [`model_of_source`]: example source text plus a language tag to a [`gob_ir::Model`]; syntax
//!   errors become hole nodes, never a failure.
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
#![expect(
    clippy::disallowed_methods,
    reason = "confinement allow list: path-to-text conversion pending migration to gob-path"
)]

mod adapter;
mod ambient;
mod crates;
mod def_use;
// frob:ticket 01M43ARY26XF7A4MSRAZ8V73JM
mod css;
mod html;
// frob:ticket 01M44YQSZ3YEXRDW9RKER9HRA2
mod csharp;
// frob:ticket 01M44YQW33GJMXQ8PQBECEBCQ1
mod dotnet;
mod fold;
mod graph;
mod markdown;
mod model;
// frob:ticket 01M47QKTN549397AFFSC3DEAQX
mod lang;
mod languages_page;
mod nodejs;
mod opaque;
mod paths;
// frob:ticket 01M3Z71542Y6NZG3G8A83EFRF2
mod actions;
mod dockerfile;
mod pin;
mod pipeline;
mod python;
mod qualifier;
mod registry;
mod rust;
// frob:ticket 01M4MC43CFCTQ7TQCHCF0C0YRR
mod source_model;
mod stdtypes;
mod symref;
mod types;
// frob:ticket 01M43ARXMH7RJ63G8096KKJF80
mod typescript;
// frob:ticket 01M44YQWGP5553K61QKC8HB0GQ
mod unity_project;
mod view;
mod yaml;

pub use actions::{ActionsAdapter, is_workflow_path};
pub use adapter::{
    Adapter, Capability, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded,
    ParseStatus, Precision,
};
pub use ambient::{AMBIENT_CLASSES, is_ambient_name};
pub use crates::CrateDeps;
pub use csharp::{
    CSharpAdapter, CsharpTest, CsharpTestFramework, csharp_test, is_csharp_path,
    is_csharp_test_file, is_csharp_test_fn, is_csharp_test_text,
};
pub use css::{CssAdapter, is_css_path};
pub use def_use::{PYTHON_SYNTAX, RUST_SYNTAX, TYPESCRIPT_SYNTAX, def_use_of, syntax_for};
pub use dockerfile::{DockerfileAdapter, is_dockerfile_path};
pub use dotnet::{
    Assignment, DotnetError, DotnetProjects, MalformedProject, Project, SolutionEntry,
    parse_project, parse_solution,
};
pub use gob_caps::Lang;
/// The facet digest scheme these digests are computed under (recorded in every lock file).
pub use gob_ir::DIGEST_SCHEME;
pub use graph::{
    CallEdge, EdgeKind, FileInfo, GapReason, ReachSet, ResolveError, Status, StatusEdge,
    SymbolGraph,
};
pub use html::{HtmlAdapter, is_html_path};
pub use lang::{lang_of_hint, lang_of_language, lang_of_tag};
pub use languages_page::languages_page;
pub use markdown::{MarkdownAdapter, slugify};
pub use model::{
    AttributeFact, CallRef, CallSite, DeriveDecl, Digests, FacetDigest, FieldDecl, FileSymbols,
    ImportEdge, LocalBinding, MapKind, MethodSig, Receiver, RefKind, RefSite, RetType, SelfKind,
    SymbolKind, SymbolRecord, UnitExtras, UnitFacts, UnitSpan, UseBinding, Visibility, collapse_ws,
};
pub use nodejs::{
    JsResolution, NodeError, NodeProjects, Package, PathAlias, TsConfig, parse_package,
};
pub use opaque::OpaqueAdapter;
pub use pipeline::{
    BuildStats, EXTRACTOR_VERSION, SkipKind, SkippedFile, build_graph, build_graph_with_stats,
    build_graph_with_stats_typed, extract_file, fold_file,
};
pub use python::{
    PythonAdapter, is_python_path, is_python_test_file, is_python_test_fn, is_python_test_module,
};
pub use qualifier::{Admit, CallQualifier};
pub use registry::{
    AdapterEntry, AdapterReport, DuplicateExtension, adapter_for, adapter_for_entry,
    adapter_for_path, adapters, fidelity_report, opaque_adapter, registry_conflicts,
};
pub use rust::RustAdapter;
pub use types::{AnnotationWeight, TypeFacts, TypesTrust};
// frob:ticket 01M4MC43CFCTQ7TQCHCF0C0YRR
pub use source_model::{model_of_source, model_of_source_at};
pub use symref::{Symref, SymrefError, Target};
pub use typescript::{
    ConstProject, Evaluated, JsxElement, JsxKind, Origin, TestItem, TestRole, TypeScriptAdapter,
    Unresolved, is_typescript_path, is_typescript_test_file, is_typescript_test_fn, is_unitless,
    jsx_elements, numeric_raw, test_items, test_unit_name,
};
pub use unity_project::{
    Assembly as UnityAssembly, TestMode as UnityTestMode, UnityAssignment, UnityProjects,
};
pub use view::model_symbols;
