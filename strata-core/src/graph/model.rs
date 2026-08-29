//! Typed node/edge model and construction-time refusal (docs/strata/graph.md).
//!
//! WHY: T-3004 section 4 places a GENERIC typed-graph kernel in strata-core,
//! separate from the parser -- node/edge KINDS and LEVEL pairing rules are
//! data the caller supplies (a schema), not hardcoded Rust enums naming
//! requirements/tests/decisions. That is what lets ticket/architecture/spec
//! instances (T-3006/T-3007, deferred) share one kernel instead of desyncing
//! two. Every malformed edge is REFUSED here, at construction, with a named
//! `GraphError` variant -- never discovered later by a separate checker.

use std::collections::{BTreeMap, BTreeSet};

/// A node identity. Caller-supplied string, unique within one `Graph`.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
pub type NodeId = String;

/// A node or edge kind name. Caller-supplied data, not a Rust enum -- kinds
/// are declared per-`GraphSchema`, not hardcoded per consumer domain.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
pub type Kind = String;

/// A level name (e.g. "requirement", "system-design", "component-unit-test").
/// Caller-supplied; the kernel only enforces relations a schema declares.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
pub type Level = String;

/// Which endpoint of an edge a `WrongEndpointKind` refusal names.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize)]
pub enum EndpointRole {
    /// The edge's source node.
    Src,
    /// The edge's destination node.
    Dst,
}

/// Every way construction can be refused. Recoverable, named, never a panic
/// -- the repo's error doctrine (no bare exceptions for caller-facing
/// mistakes; a value the caller inspects and handles).
// frob:doc docs/strata/graph.md#construction-time-refusals-grapherror
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub enum GraphError {
    /// `add_node` was given a kind the schema never declared.
    UnknownNodeKind { kind: Kind },
    /// `add_node` was given an id already present in the graph.
    DuplicateNodeId { id: NodeId },
    /// `add_node` was given a level the schema never declared.
    UnknownLevel { level: Level },
    /// `add_edge` was given a kind the schema never declared.
    UnknownEdgeKind { kind: Kind },
    /// `add_edge` names a node id with no matching node in the graph.
    DanglingEndpoint {
        edge_kind: Kind,
        role: EndpointRole,
        node: NodeId,
    },
    /// `add_edge`'s endpoint node exists but is the wrong KIND for this edge
    /// kind's schema (e.g. a `verifies` edge whose src is not a test node).
    WrongEndpointKind {
        edge_kind: Kind,
        role: EndpointRole,
        expected: BTreeSet<Kind>,
        actual: Kind,
    },
    /// `add_edge`'s endpoints violate the edge kind's declared level
    /// relation (e.g. a `verifies` edge not connecting a spec to a test at
    /// that spec's PAIRED level, T-3004 section 1).
    LevelConstraintViolation {
        edge_kind: Kind,
        src_level: Option<Level>,
        dst_level: Option<Level>,
    },
    /// `add_node`/`add_node_with_attrs` omitted an attribute key the
    /// schema requires for this node kind (T-3044 H3: a node kind can
    /// require a PAYLOAD, not just a kind/level, e.g. `test` requiring a
    /// `runnable` attr and `artifact` requiring a `code_ref` attr).
    MissingNodeAttr { kind: Kind, attr: String },
    /// `add_edge`/`add_edge_with_attrs` omitted an attribute key the
    /// schema requires for this edge kind (T-3044 H3: `supersedes` requires
    /// a `reason` attr -- change justification is a typed, required field,
    /// not optional prose).
    MissingEdgeAttr { edge_kind: Kind, attr: String },
}

/// One typed node: an id, a kind drawn from the schema, an optional level
/// (levels participate in edge-kind level constraints), and a caller-typed
/// attribute payload (T-3044 H3: a node kind can DECLARE required attrs via
/// `GraphSchema::declare_required_node_attrs`, checked at construction the
/// same way kind/level already are -- this is what lets a `test` node bind
/// to something runnable and an `artifact` node bind to real code, instead
/// of being an id with nothing behind it). Attrs are free-form
/// `String -> String` on purpose: the kernel stays domain-agnostic (it does
/// not know what a "runnable" or a "code_ref" IS), only enforcing that
/// whichever keys a schema requires are present -- the domain layer
/// (`vmodel`) is what gives those keys meaning.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Node {
    pub id: NodeId,
    pub kind: Kind,
    pub level: Option<Level>,
    pub attrs: BTreeMap<String, String>,
}

/// The level relationship an edge kind requires between its endpoints.
/// Generic on purpose: the V-model pairing (T-3004 section 1) is ONE
/// instance a caller builds from `Paired`, not a hardcoded rule here.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LevelRelation {
    /// No constraint: any levels (including none) are accepted.
    Any,
    /// Endpoints must carry the identical level (both `Some` and equal).
    Same,
    /// Endpoints must satisfy an explicit src-level -> dst-level pairing
    /// (both `Some`, and `map[src_level] == dst_level`). This is how a
    /// consumer expresses the V pairing generically: e.g.
    /// `{"requirement": "customer-test", "system-design": "subsystem-integration-test"}`.
    Paired(BTreeMap<Level, Level>),
}

/// One edge kind's construction-time contract: which node kinds may sit at
/// each endpoint, and what level relation must hold between them.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EdgeKindSchema {
    pub allowed_src_kinds: BTreeSet<Kind>,
    pub allowed_dst_kinds: BTreeSet<Kind>,
    pub level_relation: LevelRelation,
    /// Attribute keys `add_edge_with_attrs` must see for this edge kind
    /// (T-3044 H3), e.g. `supersedes` requiring `reason`. Empty means no
    /// required payload -- most edge kinds carry none.
    pub required_attrs: BTreeSet<String>,
}

impl EdgeKindSchema {
    /// Build a schema with no kind restriction on either endpoint and no
    /// level constraint -- the loosest possible edge kind (e.g. a plain
    /// `blocked_by` sequencing edge, T-3004 section 3: "survives as one
    /// edge kind among many", not exempt from the model, just unconstrained).
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn unconstrained() -> Self {
        EdgeKindSchema {
            allowed_src_kinds: BTreeSet::new(),
            allowed_dst_kinds: BTreeSet::new(),
            level_relation: LevelRelation::Any,
            required_attrs: BTreeSet::new(),
        }
    }

    /// Attach a required-attr set to an already-built schema (T-3044 H3):
    /// `EdgeKindSchema::unconstrained().require_attrs(["reason"])` is the
    /// `supersedes` case -- unconstrained on kind/level, but still typed
    /// and validated on payload.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn require_attrs(mut self, attrs: impl IntoIterator<Item = impl Into<String>>) -> Self {
        self.required_attrs = attrs.into_iter().map(Into::into).collect();
        self
    }
}

/// One directed edge: a kind, the src/dst node ids it connects, and a
/// caller-typed attribute payload (T-3044 H3), e.g. a `supersedes` edge's
/// required `reason` attr -- the change justification it must carry.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Edge {
    pub kind: Kind,
    pub src: NodeId,
    pub dst: NodeId,
    pub attrs: BTreeMap<String, String>,
}

/// The caller-supplied vocabulary a `Graph` type-checks against: legal node
/// kinds, legal levels, and per-edge-kind endpoint/level contracts. This is
/// the whole "generic, not spec-specific" design constraint made concrete --
/// a ticket/architecture instance builds its OWN schema; the kernel does not
/// name `requirement`/`test`/`decision` anywhere in its own code.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
#[derive(Debug, Clone, Default)]
pub struct GraphSchema {
    pub node_kinds: BTreeSet<Kind>,
    pub levels: BTreeSet<Level>,
    pub edge_kinds: BTreeMap<Kind, EdgeKindSchema>,
    /// Attribute keys `add_node_with_attrs` must see for a given node kind
    /// (T-3044 H3), e.g. `test` requiring `runnable` and `artifact`
    /// requiring `code_ref`. A kind absent from this map requires nothing.
    pub required_node_attrs: BTreeMap<Kind, BTreeSet<String>>,
}

impl GraphSchema {
    /// An empty schema: no node kinds, no levels, no edge kinds declared
    /// yet. Callers build one up via `declare_node_kind`/`declare_level`/
    /// `declare_edge_kind`.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn new() -> Self {
        GraphSchema::default()
    }

    /// Add a legal node kind. Idempotent: declaring the same kind twice is
    /// not an error (schema *declaration* is additive, unlike graph
    /// construction which refuses duplicates).
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn declare_node_kind(&mut self, kind: impl Into<Kind>) -> &mut Self {
        self.node_kinds.insert(kind.into());
        self
    }

    /// Add a legal level name.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn declare_level(&mut self, level: impl Into<Level>) -> &mut Self {
        self.levels.insert(level.into());
        self
    }

    /// Add or replace an edge kind's construction-time contract.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn declare_edge_kind(
        &mut self,
        kind: impl Into<Kind>,
        schema: EdgeKindSchema,
    ) -> &mut Self {
        self.edge_kinds.insert(kind.into(), schema);
        self
    }

    /// Require `attrs` to be present (via `add_node_with_attrs`) on every
    /// node of `kind` (T-3044 H3). Replaces any previously declared
    /// requirement for the same kind.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn declare_required_node_attrs(
        &mut self,
        kind: impl Into<Kind>,
        attrs: impl IntoIterator<Item = impl Into<String>>,
    ) -> &mut Self {
        self.required_node_attrs
            .insert(kind.into(), attrs.into_iter().map(Into::into).collect());
        self
    }
}

/// A typed graph: a fixed `GraphSchema` plus the nodes and edges added
/// against it. Every mutation is refuse-or-commit -- there is no path to a
/// graph value that holds a malformed edge (T-3004 section 4's "type
/// checked" requirement, enforced here rather than left to a later pass).
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
#[derive(Debug, Clone)]
pub struct Graph {
    schema: GraphSchema,
    nodes: BTreeMap<NodeId, Node>,
    edges: Vec<Edge>,
}

impl Graph {
    /// Start an empty graph typed against `schema`.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn new(schema: GraphSchema) -> Self {
        Graph {
            schema,
            nodes: BTreeMap::new(),
            edges: Vec::new(),
        }
    }

    /// This graph's schema (read-only: the schema is fixed for the life of
    /// the graph, so queries and later edge additions stay consistent).
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn schema(&self) -> &GraphSchema {
        &self.schema
    }

    /// All node ids currently in the graph, in id order.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn node_ids(&self) -> impl Iterator<Item = &NodeId> {
        self.nodes.keys()
    }

    /// Look up a node by id.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn node(&self, id: &str) -> Option<&Node> {
        self.nodes.get(id)
    }

    /// All edges currently in the graph, in insertion order.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn edges(&self) -> &[Edge] {
        &self.edges
    }

    /// Add a typed node. Refuses (leaving the graph unchanged) if `kind` is
    /// not declared in the schema, if `level` is given but not declared, or
    /// if `id` already names a node.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn add_node(
        &mut self,
        id: impl Into<NodeId>,
        kind: impl Into<Kind>,
        level: Option<Level>,
    ) -> Result<(), GraphError> {
        self.add_node_with_attrs(id, kind, level, BTreeMap::new())
    }

    /// Add a typed node carrying an attribute payload (T-3044 H3). Same
    /// refusals as `add_node`, PLUS: refuses if the schema's
    /// `required_node_attrs` for this kind names a key absent from `attrs`.
    /// `add_node` is a thin wrapper over this with an empty payload -- a
    /// kind with no required attrs behaves identically either way; a kind
    /// that DOES require attrs (`test`, `artifact` in the V-model schema)
    /// can only be constructed through this entry point.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn add_node_with_attrs(
        &mut self,
        id: impl Into<NodeId>,
        kind: impl Into<Kind>,
        level: Option<Level>,
        attrs: BTreeMap<String, String>,
    ) -> Result<(), GraphError> {
        let id = id.into();
        let kind = kind.into();
        if !self.schema.node_kinds.contains(&kind) {
            return Err(GraphError::UnknownNodeKind { kind });
        }
        if let Some(ref lvl) = level {
            if !self.schema.levels.contains(lvl) {
                return Err(GraphError::UnknownLevel { level: lvl.clone() });
            }
        }
        if self.nodes.contains_key(&id) {
            return Err(GraphError::DuplicateNodeId { id });
        }
        if let Some(required) = self.schema.required_node_attrs.get(&kind) {
            for attr in required {
                if !attrs.contains_key(attr) {
                    return Err(GraphError::MissingNodeAttr {
                        kind,
                        attr: attr.clone(),
                    });
                }
            }
        }
        self.nodes.insert(
            id.clone(),
            Node {
                id,
                kind,
                level,
                attrs,
            },
        );
        Ok(())
    }

    /// Add a typed edge. Refuses (leaving the graph unchanged) on: an
    /// undeclared edge kind, a dangling endpoint (no such node), an
    /// endpoint whose node kind the edge kind's schema does not allow, or a
    /// level relationship the edge kind's schema requires but the
    /// endpoints' levels do not satisfy.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn add_edge(
        &mut self,
        kind: impl Into<Kind>,
        src: impl Into<NodeId>,
        dst: impl Into<NodeId>,
    ) -> Result<(), GraphError> {
        self.add_edge_with_attrs(kind, src, dst, BTreeMap::new())
    }

    /// Add a typed edge carrying an attribute payload (T-3044 H3). Same
    /// refusals as `add_edge`, PLUS: refuses if the edge kind's
    /// `required_attrs` names a key absent from `attrs` -- this is what
    /// makes `supersedes` unable to be constructed without a `reason`.
    /// `add_edge` is a thin wrapper over this with an empty payload.
// frob:doc docs/strata/graph.md#model-strata-coresrcgraphmodelrs
    pub fn add_edge_with_attrs(
        &mut self,
        kind: impl Into<Kind>,
        src: impl Into<NodeId>,
        dst: impl Into<NodeId>,
        attrs: BTreeMap<String, String>,
    ) -> Result<(), GraphError> {
        let kind = kind.into();
        let src = src.into();
        let dst = dst.into();

        let edge_schema = self
            .schema
            .edge_kinds
            .get(&kind)
            .ok_or_else(|| GraphError::UnknownEdgeKind { kind: kind.clone() })?
            .clone();

        let src_node = self
            .nodes
            .get(&src)
            .ok_or_else(|| GraphError::DanglingEndpoint {
                edge_kind: kind.clone(),
                role: EndpointRole::Src,
                node: src.clone(),
            })?;
        let dst_node = self
            .nodes
            .get(&dst)
            .ok_or_else(|| GraphError::DanglingEndpoint {
                edge_kind: kind.clone(),
                role: EndpointRole::Dst,
                node: dst.clone(),
            })?;

        if !edge_schema.allowed_src_kinds.is_empty()
            && !edge_schema.allowed_src_kinds.contains(&src_node.kind)
        {
            return Err(GraphError::WrongEndpointKind {
                edge_kind: kind,
                role: EndpointRole::Src,
                expected: edge_schema.allowed_src_kinds,
                actual: src_node.kind.clone(),
            });
        }
        if !edge_schema.allowed_dst_kinds.is_empty()
            && !edge_schema.allowed_dst_kinds.contains(&dst_node.kind)
        {
            return Err(GraphError::WrongEndpointKind {
                edge_kind: kind,
                role: EndpointRole::Dst,
                expected: edge_schema.allowed_dst_kinds,
                actual: dst_node.kind.clone(),
            });
        }

        match &edge_schema.level_relation {
            LevelRelation::Any => {}
            LevelRelation::Same => {
                let ok = matches!((&src_node.level, &dst_node.level), (Some(a), Some(b)) if a == b);
                if !ok {
                    return Err(GraphError::LevelConstraintViolation {
                        edge_kind: kind,
                        src_level: src_node.level.clone(),
                        dst_level: dst_node.level.clone(),
                    });
                }
            }
            LevelRelation::Paired(map) => {
                let ok = match (&src_node.level, &dst_node.level) {
                    (Some(s), Some(d)) => map.get(s) == Some(d),
                    _ => false,
                };
                if !ok {
                    return Err(GraphError::LevelConstraintViolation {
                        edge_kind: kind,
                        src_level: src_node.level.clone(),
                        dst_level: dst_node.level.clone(),
                    });
                }
            }
        }

        for attr in &edge_schema.required_attrs {
            if !attrs.contains_key(attr) {
                return Err(GraphError::MissingEdgeAttr {
                    edge_kind: kind,
                    attr: attr.clone(),
                });
            }
        }

        self.edges.push(Edge {
            kind,
            src,
            dst,
            attrs,
        });
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn v_model_schema() -> GraphSchema {
        let mut s = GraphSchema::new();
        s.declare_node_kind("requirement")
            .declare_node_kind("design")
            .declare_node_kind("test")
            .declare_level("requirement-level")
            .declare_level("test-level");
        // `verifies` edges run test -> requirement (src=test, dst=requirement),
        // so the pairing is keyed by src (test) level -> required dst
        // (requirement) level.
        let mut pairing = BTreeMap::new();
        pairing.insert("test-level".to_string(), "requirement-level".to_string());
        s.declare_edge_kind(
            "verifies",
            EdgeKindSchema {
                allowed_src_kinds: BTreeSet::from(["test".to_string()]),
                allowed_dst_kinds: BTreeSet::from(["requirement".to_string()]),
                level_relation: LevelRelation::Paired(pairing),
                required_attrs: BTreeSet::new(),
            },
        );
        s.declare_edge_kind(
            "satisfies",
            EdgeKindSchema {
                allowed_src_kinds: BTreeSet::from(["design".to_string()]),
                allowed_dst_kinds: BTreeSet::from(["requirement".to_string()]),
                level_relation: LevelRelation::Any,
                required_attrs: BTreeSet::new(),
            },
        );
        s.declare_edge_kind("blocked_by", EdgeKindSchema::unconstrained());
        s
    }

    #[test]
    // frob:ticket T-3005
    fn add_node_rejects_undeclared_kind() {
        let mut g = Graph::new(v_model_schema());
        let err = g.add_node("r1", "gadget", None).unwrap_err();
        assert_eq!(
            err,
            GraphError::UnknownNodeKind {
                kind: "gadget".into()
            }
        );
    }

    #[test]
    // frob:ticket T-3005
    fn add_node_rejects_duplicate_id() {
        let mut g = Graph::new(v_model_schema());
        g.add_node("r1", "requirement", None).unwrap();
        let err = g.add_node("r1", "requirement", None).unwrap_err();
        assert_eq!(err, GraphError::DuplicateNodeId { id: "r1".into() });
    }

    #[test]
    // frob:ticket T-3005
    fn add_node_rejects_undeclared_level() {
        let mut g = Graph::new(v_model_schema());
        let err = g
            .add_node("r1", "requirement", Some("orbital".into()))
            .unwrap_err();
        assert_eq!(
            err,
            GraphError::UnknownLevel {
                level: "orbital".into()
            }
        );
    }

    #[test]
    // frob:ticket T-3005
    fn add_edge_rejects_undeclared_kind() {
        let mut g = Graph::new(v_model_schema());
        g.add_node("r1", "requirement", None).unwrap();
        g.add_node("t1", "test", None).unwrap();
        let err = g.add_edge("decides", "t1", "r1").unwrap_err();
        assert_eq!(
            err,
            GraphError::UnknownEdgeKind {
                kind: "decides".into()
            }
        );
    }

    #[test]
    // frob:ticket T-3005
    fn add_edge_rejects_dangling_endpoint() {
        let mut g = Graph::new(v_model_schema());
        g.add_node("t1", "test", None).unwrap();
        let err = g.add_edge("verifies", "t1", "ghost").unwrap_err();
        assert_eq!(
            err,
            GraphError::DanglingEndpoint {
                edge_kind: "verifies".into(),
                role: EndpointRole::Dst,
                node: "ghost".into(),
            }
        );
    }

    #[test]
    // frob:ticket T-3005
    fn add_edge_rejects_wrong_endpoint_kind() {
        let mut g = Graph::new(v_model_schema());
        g.add_node("r1", "requirement", None).unwrap();
        g.add_node("r2", "requirement", None).unwrap();
        // `verifies` requires a `test` src -- feeding it a requirement must refuse.
        let err = g.add_edge("verifies", "r1", "r2").unwrap_err();
        match err {
            GraphError::WrongEndpointKind { role, .. } => assert_eq!(role, EndpointRole::Src),
            other => panic!("expected WrongEndpointKind, got {:?}", other),
        }
    }

    #[test]
    // frob:ticket T-3005
    fn add_edge_rejects_unpaired_levels() {
        let mut g = Graph::new(v_model_schema());
        g.add_node("r1", "requirement", Some("requirement-level".into()))
            .unwrap();
        // t1 is at the WRONG level for r1's pairing (should be "test-level").
        g.add_node("t1", "test", Some("requirement-level".into()))
            .unwrap();
        let err = g.add_edge("verifies", "t1", "r1").unwrap_err();
        assert_eq!(
            err,
            GraphError::LevelConstraintViolation {
                edge_kind: "verifies".into(),
                src_level: Some("requirement-level".into()),
                dst_level: Some("requirement-level".into()),
            }
        );
    }

    #[test]
    // frob:ticket T-3005
    fn add_edge_accepts_correctly_paired_levels() {
        let mut g = Graph::new(v_model_schema());
        g.add_node("r1", "requirement", Some("requirement-level".into()))
            .unwrap();
        g.add_node("t1", "test", Some("test-level".into())).unwrap();
        g.add_edge("verifies", "t1", "r1").unwrap();
        assert_eq!(g.edges().len(), 1);
    }

    #[test]
    // frob:ticket T-3005
    fn unconstrained_edge_kind_accepts_any_kinds_and_levels() {
        let mut g = Graph::new(v_model_schema());
        g.add_node("r1", "requirement", None).unwrap();
        g.add_node("r2", "requirement", None).unwrap();
        g.add_edge("blocked_by", "r1", "r2").unwrap();
        assert_eq!(g.edges().len(), 1);
    }

    #[test]
    // frob:ticket T-3078
    fn declare_node_kind_registers_kind_and_is_idempotent() {
        let mut s = GraphSchema::new();
        s.declare_node_kind("requirement");
        assert!(s.node_kinds.contains("requirement"));
        // Declaring the same kind twice is additive, not an error.
        s.declare_node_kind("requirement");
        assert_eq!(s.node_kinds.len(), 1);
    }

    #[test]
    // frob:ticket T-3078
    fn declare_level_registers_level() {
        let mut s = GraphSchema::new();
        s.declare_level("requirement-level");
        assert!(s.levels.contains("requirement-level"));
    }

    #[test]
    // frob:ticket T-3078
    fn declare_edge_kind_registers_and_replaces_contract() {
        let mut s = GraphSchema::new();
        s.declare_edge_kind("blocked_by", EdgeKindSchema::unconstrained());
        assert!(s.edge_kinds.contains_key("blocked_by"));
        assert_eq!(
            s.edge_kinds["blocked_by"].level_relation,
            LevelRelation::Any
        );
        // Declaring the same kind again REPLACES the prior contract.
        s.declare_edge_kind(
            "blocked_by",
            EdgeKindSchema::unconstrained().require_attrs(["reason"]),
        );
        assert!(s.edge_kinds["blocked_by"]
            .required_attrs
            .contains("reason"));
    }

    #[test]
    // frob:ticket T-3078
    fn require_attrs_populates_required_attrs_set() {
        let schema = EdgeKindSchema::unconstrained().require_attrs(["reason"]);
        assert_eq!(
            schema.required_attrs,
            BTreeSet::from(["reason".to_string()])
        );
    }

    #[test]
    // frob:ticket T-3078
    fn declare_required_node_attrs_populates_schema_map() {
        let mut s = GraphSchema::new();
        s.declare_required_node_attrs("test", ["runnable"]);
        assert_eq!(
            s.required_node_attrs["test"],
            BTreeSet::from(["runnable".to_string()])
        );
    }

    #[test]
    // frob:ticket T-3078
    fn add_node_with_attrs_refuses_missing_required_attr() {
        let mut s = GraphSchema::new();
        s.declare_node_kind("test");
        s.declare_required_node_attrs("test", ["runnable"]);
        let mut g = Graph::new(s);
        let err = g
            .add_node_with_attrs("t1", "test", None, BTreeMap::new())
            .unwrap_err();
        assert_eq!(
            err,
            GraphError::MissingNodeAttr {
                kind: "test".into(),
                attr: "runnable".into(),
            }
        );
        // Supplying the required attr succeeds and the node carries it.
        let mut attrs = BTreeMap::new();
        attrs.insert("runnable".to_string(), "pytest::test_x".to_string());
        g.add_node_with_attrs("t2", "test", None, attrs.clone())
            .unwrap();
        assert_eq!(g.node("t2").unwrap().attrs, attrs);
    }

    #[test]
    // frob:ticket T-3078
    fn add_edge_with_attrs_refuses_missing_required_attr() {
        let mut s = GraphSchema::new();
        s.declare_node_kind("decision");
        s.declare_edge_kind(
            "supersedes",
            EdgeKindSchema::unconstrained().require_attrs(["reason"]),
        );
        let mut g = Graph::new(s);
        g.add_node("d1", "decision", None).unwrap();
        g.add_node("d2", "decision", None).unwrap();
        let err = g
            .add_edge_with_attrs("supersedes", "d1", "d2", BTreeMap::new())
            .unwrap_err();
        assert_eq!(
            err,
            GraphError::MissingEdgeAttr {
                edge_kind: "supersedes".into(),
                attr: "reason".into(),
            }
        );
        // Supplying the required attr succeeds and the edge carries it.
        let mut attrs = BTreeMap::new();
        attrs.insert("reason".to_string(), "renamed for clarity".to_string());
        g.add_edge_with_attrs("supersedes", "d1", "d2", attrs.clone())
            .unwrap();
        assert_eq!(g.edges()[0].attrs, attrs);
    }
}
