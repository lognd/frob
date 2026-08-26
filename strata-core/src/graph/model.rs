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
pub type NodeId = String;

/// A node or edge kind name. Caller-supplied data, not a Rust enum -- kinds
/// are declared per-`GraphSchema`, not hardcoded per consumer domain.
pub type Kind = String;

/// A level name (e.g. "requirement", "system-design", "component-unit-test").
/// Caller-supplied; the kernel only enforces relations a schema declares.
pub type Level = String;

/// Which endpoint of an edge a `WrongEndpointKind` refusal names.
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
    DanglingEndpoint { edge_kind: Kind, role: EndpointRole, node: NodeId },
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
}

/// One typed node: an id, a kind drawn from the schema, and an optional
/// level (levels participate in edge-kind level constraints).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Node {
    pub id: NodeId,
    pub kind: Kind,
    pub level: Option<Level>,
}

/// The level relationship an edge kind requires between its endpoints.
/// Generic on purpose: the V-model pairing (T-3004 section 1) is ONE
/// instance a caller builds from `Paired`, not a hardcoded rule here.
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
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EdgeKindSchema {
    pub allowed_src_kinds: BTreeSet<Kind>,
    pub allowed_dst_kinds: BTreeSet<Kind>,
    pub level_relation: LevelRelation,
}

impl EdgeKindSchema {
    /// Build a schema with no kind restriction on either endpoint and no
    /// level constraint -- the loosest possible edge kind (e.g. a plain
    /// `blocked_by` sequencing edge, T-3004 section 3: "survives as one
    /// edge kind among many", not exempt from the model, just unconstrained).
    pub fn unconstrained() -> Self {
        EdgeKindSchema {
            allowed_src_kinds: BTreeSet::new(),
            allowed_dst_kinds: BTreeSet::new(),
            level_relation: LevelRelation::Any,
        }
    }
}

/// One directed edge: a kind plus the src/dst node ids it connects.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Edge {
    pub kind: Kind,
    pub src: NodeId,
    pub dst: NodeId,
}

/// The caller-supplied vocabulary a `Graph` type-checks against: legal node
/// kinds, legal levels, and per-edge-kind endpoint/level contracts. This is
/// the whole "generic, not spec-specific" design constraint made concrete --
/// a ticket/architecture instance builds its OWN schema; the kernel does not
/// name `requirement`/`test`/`decision` anywhere in its own code.
#[derive(Debug, Clone, Default)]
pub struct GraphSchema {
    pub node_kinds: BTreeSet<Kind>,
    pub levels: BTreeSet<Level>,
    pub edge_kinds: BTreeMap<Kind, EdgeKindSchema>,
}

impl GraphSchema {
    /// An empty schema: no node kinds, no levels, no edge kinds declared
    /// yet. Callers build one up via `declare_node_kind`/`declare_level`/
    /// `declare_edge_kind`.
    pub fn new() -> Self {
        GraphSchema::default()
    }

    /// Add a legal node kind. Idempotent: declaring the same kind twice is
    /// not an error (schema *declaration* is additive, unlike graph
    /// construction which refuses duplicates).
    pub fn declare_node_kind(&mut self, kind: impl Into<Kind>) -> &mut Self {
        self.node_kinds.insert(kind.into());
        self
    }

    /// Add a legal level name.
    pub fn declare_level(&mut self, level: impl Into<Level>) -> &mut Self {
        self.levels.insert(level.into());
        self
    }

    /// Add or replace an edge kind's construction-time contract.
    pub fn declare_edge_kind(&mut self, kind: impl Into<Kind>, schema: EdgeKindSchema) -> &mut Self {
        self.edge_kinds.insert(kind.into(), schema);
        self
    }
}

/// A typed graph: a fixed `GraphSchema` plus the nodes and edges added
/// against it. Every mutation is refuse-or-commit -- there is no path to a
/// graph value that holds a malformed edge (T-3004 section 4's "type
/// checked" requirement, enforced here rather than left to a later pass).
#[derive(Debug, Clone)]
pub struct Graph {
    schema: GraphSchema,
    nodes: BTreeMap<NodeId, Node>,
    edges: Vec<Edge>,
}

impl Graph {
    /// Start an empty graph typed against `schema`.
    pub fn new(schema: GraphSchema) -> Self {
        Graph {
            schema,
            nodes: BTreeMap::new(),
            edges: Vec::new(),
        }
    }

    /// This graph's schema (read-only: the schema is fixed for the life of
    /// the graph, so queries and later edge additions stay consistent).
    pub fn schema(&self) -> &GraphSchema {
        &self.schema
    }

    /// All node ids currently in the graph, in id order.
    pub fn node_ids(&self) -> impl Iterator<Item = &NodeId> {
        self.nodes.keys()
    }

    /// Look up a node by id.
    pub fn node(&self, id: &str) -> Option<&Node> {
        self.nodes.get(id)
    }

    /// All edges currently in the graph, in insertion order.
    pub fn edges(&self) -> &[Edge] {
        &self.edges
    }

    /// Add a typed node. Refuses (leaving the graph unchanged) if `kind` is
    /// not declared in the schema, if `level` is given but not declared, or
    /// if `id` already names a node.
    pub fn add_node(
        &mut self,
        id: impl Into<NodeId>,
        kind: impl Into<Kind>,
        level: Option<Level>,
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
        self.nodes.insert(id.clone(), Node { id, kind, level });
        Ok(())
    }

    /// Add a typed edge. Refuses (leaving the graph unchanged) on: an
    /// undeclared edge kind, a dangling endpoint (no such node), an
    /// endpoint whose node kind the edge kind's schema does not allow, or a
    /// level relationship the edge kind's schema requires but the
    /// endpoints' levels do not satisfy.
    pub fn add_edge(
        &mut self,
        kind: impl Into<Kind>,
        src: impl Into<NodeId>,
        dst: impl Into<NodeId>,
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

        let src_node = self.nodes.get(&src).ok_or_else(|| GraphError::DanglingEndpoint {
            edge_kind: kind.clone(),
            role: EndpointRole::Src,
            node: src.clone(),
        })?;
        let dst_node = self.nodes.get(&dst).ok_or_else(|| GraphError::DanglingEndpoint {
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

        self.edges.push(Edge { kind, src, dst });
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
            },
        );
        s.declare_edge_kind(
            "satisfies",
            EdgeKindSchema {
                allowed_src_kinds: BTreeSet::from(["design".to_string()]),
                allowed_dst_kinds: BTreeSet::from(["requirement".to_string()]),
                level_relation: LevelRelation::Any,
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
        assert_eq!(err, GraphError::UnknownNodeKind { kind: "gadget".into() });
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
        assert_eq!(err, GraphError::UnknownLevel { level: "orbital".into() });
    }

    #[test]
    // frob:ticket T-3005
    fn add_edge_rejects_undeclared_kind() {
        let mut g = Graph::new(v_model_schema());
        g.add_node("r1", "requirement", None).unwrap();
        g.add_node("t1", "test", None).unwrap();
        let err = g.add_edge("decides", "t1", "r1").unwrap_err();
        assert_eq!(err, GraphError::UnknownEdgeKind { kind: "decides".into() });
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
}
