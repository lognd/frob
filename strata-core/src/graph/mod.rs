//! Generic typed-graph kernel (docs/strata/graph.md, T-3004 section 4): typed
//! nodes, typed edges, level constraints, bidirectional closure, reachability
//! and cycle detection. Lives BESIDE `crate::parse`, not inside it -- this
//! module knows nothing about the strata surface grammar and the parser
//! knows nothing about this module. Node/edge KIND NAMES and LEVEL PAIRINGS
//! are data a caller supplies via `GraphSchema`, never hardcoded here: this
//! crate does not know what a "requirement" or a "test" is. That is what
//! lets ticket/architecture/spec instances (T-3006/T-3007, deferred by the
//! epic) share one kernel instead of each growing its own bespoke graph.

pub mod model;
pub mod query;

/// The V-model spec graph (T-3004 sections 1-2, T-3007): the FIRST
/// consumer of this generic kernel -- node/edge kinds, the paired-level
/// V-model schema, and the four structural closure rules. See
/// `vmodel`'s module doc for why this lives beside, not inside, the
/// generic model/query modules.
pub mod vmodel;

pub use model::{
    Edge, EdgeKindSchema, EndpointRole, Graph, GraphError, GraphSchema, Kind, Level, LevelRelation,
    Node, NodeId,
};
pub use query::KindFilter;
