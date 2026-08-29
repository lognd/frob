//! Structural closure rules for the V-model graph (T-3004 section 2,
//! T-3044 H2/H3): the five rules that decide whether a `vmodel` graph is
//! COMPLETE (every requirement traced and tested, no orphans, no trace
//! cycle) -- split out of `vmodel`'s top-level module (T-3260) once the
//! combined schema+closure file crossed the LARGE001 threshold. Depends
//! on `super`'s node/edge kind constants and level pairing, so this
//! module is only ever meaningful alongside `vmodel::v_model_schema`.

use super::{
    v_pairing, EDGE_ALLOCATES, EDGE_REFINES, EDGE_SATISFIES, EDGE_VERIFIES, KIND_ARTIFACT,
    KIND_TEST,
};
use crate::graph::model::{Graph, Level, NodeId};
use crate::graph::query::KindFilter;

/// One closure-rule violation, named so a caller (CLI or PyO3 boundary)
/// can render it without re-deriving which rule fired.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
// frob:doc docs/strata/vmodel.md#the-five-closure-rules-t-3004-section-2
// frob:ticket T-3260
pub enum ClosureViolation {
    /// Rule 1: this requirement/artifact node has no incoming `satisfies`
    /// edge from any design element -- an orphan requirement.
    OrphanRequirement { node: NodeId },
    /// Rule 2: this design/artifact node has no outgoing `satisfies` edge
    /// to any requirement -- unjustified code.
    UnjustifiedDesign { node: NodeId },
    /// Rule 3: this artifact node has no incoming `verifies` edge from a
    /// test at its PAIRED level -- an untested requirement. It may still
    /// have `verifies` edges from tests at the WRONG level; the kernel's
    /// own `LevelConstraintViolation` already refuses those at construction
    /// time, so a graph that got this far has none -- this rule instead
    /// catches the case of ZERO verifying edges at all.
    UntestedArtifact { node: NodeId },
    /// Rule 4: this test node has no outgoing `verifies` edge to anything
    /// -- an orphan test.
    OrphanTest { node: NodeId },
    /// Rule 5: a cycle exists among `satisfies`/`refines`/`allocates`
    /// edges -- the trace subgraph must be a DAG, since "traces up to a
    /// requirement" is meaningless if the trace can loop back on itself.
    /// `cycle` is the witness path `find_cycle` returned (T-3043: a bare
    /// bool cycle checker has shipped blind to a real planted cycle in
    /// this repo before; keep the witness).
    TraceCycle { cycle: Vec<NodeId> },
}

/// Every node of `kind` in `graph`, in id order -- shared by all four rules
/// below so each only has to state its own edge-direction/edge-kind logic.
// frob:ticket T-3260
fn nodes_of_kind<'g>(graph: &'g Graph, kind: &str) -> Vec<&'g NodeId> {
    graph
        .node_ids()
        .filter(|id| graph.node(id).map(|n| n.kind == kind).unwrap_or(false))
        .collect()
}

/// The left-side V-model levels ordered outermost (`requirements`) first,
/// innermost (`component-design`) last -- shared by rules 1 and 2 so each
/// can exempt the one boundary level that structurally cannot satisfy the
/// rule (there is nothing more detailed than `component-design` to satisfy
/// IT, and nothing above `requirements` for it to trace up to).
// frob:ticket T-3260
fn left_levels_outermost_first() -> Vec<Level> {
    v_pairing().into_iter().map(|(left, _right)| left).collect()
}

/// True if `level` is the OUTERMOST left-side level (`requirements`) --
/// rule 2 exempts it, since a top-level requirement has nothing further up
/// to trace to. A node with no level at all is never exempt (unknown
/// position is the conservative default: still required to justify).
// frob:ticket T-3260
fn is_outermost_level(level: &Option<Level>) -> bool {
    matches!(level, Some(l) if left_levels_outermost_first().first() == Some(l))
}

/// True if `level` is the INNERMOST left-side level (`component-design`) --
/// rule 1 exempts it, since nothing more detailed exists to satisfy IT.
// frob:ticket T-3260
fn is_innermost_level(level: &Option<Level>) -> bool {
    matches!(level, Some(l) if left_levels_outermost_first().last() == Some(l))
}

/// The three edge kinds that make up the "traces up toward a requirement"
/// relation -- shared by rule 2 (forward: does this design reach a real
/// requirement) and rule 5 (is that relation even acyclic). T-3043: this
/// set previously backed only an emptiness check; it now backs a real
/// reachability-to-an-endpoint check for rules 1/2 as well.
// frob:ticket T-3260
fn trace_kinds() -> std::collections::BTreeSet<String> {
    [
        EDGE_SATISFIES.to_string(),
        EDGE_REFINES.to_string(),
        EDGE_ALLOCATES.to_string(),
    ]
    .into()
}

/// True if any node in `closure` is a `KIND_ARTIFACT` node at exactly
/// `level`. Used to turn a closure-set from "is it non-empty" into
/// "does it actually contain the endpoint that makes the path meaningful"
/// (T-3043 H2: a mutual-`satisfies` pair with no requirement anywhere in
/// the graph has a non-empty closure but never reaches a requirement).
// frob:ticket T-3260
fn closure_reaches_level(
    graph: &Graph,
    closure: &std::collections::BTreeSet<NodeId>,
    level: &str,
) -> bool {
    closure.iter().any(|id| {
        graph
            .node(id)
            .map(|n| n.kind == KIND_ARTIFACT && n.level.as_deref() == Some(level))
            .unwrap_or(false)
    })
}

/// Rule 1: every artifact node OTHER THAN the innermost level
/// (`component-design`, which has nothing more detailed to satisfy it)
/// must have >=1 incoming `satisfies` edge. Returns one
/// `OrphanRequirement` per violating node, empty if none.
// frob:doc docs/strata/vmodel.md#the-five-closure-rules-t-3004-section-2
// frob:ticket T-3260
pub fn check_no_orphan_requirements(graph: &Graph) -> Vec<ClosureViolation> {
    let filter_set = [EDGE_SATISFIES.to_string()].into();
    let filter = KindFilter::Only(&filter_set);
    let innermost = left_levels_outermost_first().last().cloned();
    nodes_of_kind(graph, KIND_ARTIFACT)
        .into_iter()
        .filter(|id| !is_innermost_level(&graph.node(id).and_then(|n| n.level.clone())))
        .filter(|id| {
            // T-3043: a non-empty backward closure is not enough -- it must
            // actually reach a real, grounded design (the innermost level)
            // rather than looping among peers with nothing underneath them.
            let closure = graph.backward_closure(id, &filter);
            match &innermost {
                Some(lvl) => !closure_reaches_level(graph, &closure, lvl),
                None => closure.is_empty(),
            }
        })
        .map(|id| ClosureViolation::OrphanRequirement { node: id.clone() })
        .collect()
}

/// Rule 2: every artifact node OTHER THAN the outermost level
/// (`requirements`, which has nothing above it to trace to) must have >=1
/// outgoing edge among `satisfies`/`refines`/`allocates` -- some route
/// tracing it back up to a requirement. Catches unjustified code: a design
/// element (or intermediate spec) tracing to nothing.
// frob:doc docs/strata/vmodel.md#the-five-closure-rules-t-3004-section-2
// frob:ticket T-3260
pub fn check_no_unjustified_design(graph: &Graph) -> Vec<ClosureViolation> {
    let kinds = trace_kinds();
    let filter = KindFilter::Only(&kinds);
    let outermost = left_levels_outermost_first().first().cloned();
    nodes_of_kind(graph, KIND_ARTIFACT)
        .into_iter()
        .filter(|id| !is_outermost_level(&graph.node(id).and_then(|n| n.level.clone())))
        .filter(|id| {
            // T-3043 H2: a non-empty forward closure is not enough -- it
            // must actually reach a real requirements-level node, not just
            // some other design element that itself traces to nothing (the
            // mutual-satisfies-pair-with-zero-requirements escape).
            let closure = graph.forward_closure(id, &filter);
            match &outermost {
                Some(lvl) => !closure_reaches_level(graph, &closure, lvl),
                None => closure.is_empty(),
            }
        })
        .map(|id| ClosureViolation::UnjustifiedDesign { node: id.clone() })
        .collect()
}

/// Rule 3: every artifact node must have >=1 incoming `verifies` edge.
/// The kernel already refuses (at construction) any `verifies` edge whose
/// endpoints are not at the schema's paired levels, so any surviving
/// incoming `verifies` edge is necessarily at the paired level -- this
/// rule only needs to check for the presence of at least one.
// frob:doc docs/strata/vmodel.md#the-five-closure-rules-t-3004-section-2
// frob:ticket T-3260
pub fn check_no_untested_artifact(graph: &Graph) -> Vec<ClosureViolation> {
    let filter_set = [EDGE_VERIFIES.to_string()].into();
    let filter = KindFilter::Only(&filter_set);
    nodes_of_kind(graph, KIND_ARTIFACT)
        .into_iter()
        .filter(|id| graph.backward_closure(id, &filter).is_empty())
        .map(|id| ClosureViolation::UntestedArtifact { node: id.clone() })
        .collect()
}

/// Rule 4: every test node must have >=1 outgoing `verifies` edge.
// frob:doc docs/strata/vmodel.md#the-five-closure-rules-t-3004-section-2
// frob:ticket T-3260
pub fn check_no_orphan_test(graph: &Graph) -> Vec<ClosureViolation> {
    let filter_set = [EDGE_VERIFIES.to_string()].into();
    let filter = KindFilter::Only(&filter_set);
    nodes_of_kind(graph, KIND_TEST)
        .into_iter()
        .filter(|id| graph.forward_closure(id, &filter).is_empty())
        .map(|id| ClosureViolation::OrphanTest { node: id.clone() })
        .collect()
}

/// Rule 5: the trace subgraph (`satisfies`/`refines`/`allocates`) must be
/// acyclic. `find_cycle` already exists in the kernel and returns a
/// witness path; T-3043 wires it in here since nothing previously called
/// it from `check_closure`.
// frob:doc docs/strata/vmodel.md#the-five-closure-rules-t-3004-section-2
// frob:ticket T-3260
pub fn check_no_trace_cycle(graph: &Graph) -> Vec<ClosureViolation> {
    let kinds = trace_kinds();
    let filter = KindFilter::Only(&kinds);
    match graph.find_cycle(&filter) {
        Some(cycle) => vec![ClosureViolation::TraceCycle { cycle }],
        None => Vec::new(),
    }
}

/// Run all five rules and concatenate their violations, in rule order
/// (1, 2, 3, 4, 5). Empty means the graph is structurally closed --
/// T-3004 section 2's "bad-but-complete passes" bar, nothing about quality.
// frob:doc docs/strata/vmodel.md#the-five-closure-rules-t-3004-section-2
// frob:ticket T-3260
pub fn check_closure(graph: &Graph) -> Vec<ClosureViolation> {
    let mut out = check_no_orphan_requirements(graph);
    out.extend(check_no_unjustified_design(graph));
    out.extend(check_no_untested_artifact(graph));
    out.extend(check_no_orphan_test(graph));
    out.extend(check_no_trace_cycle(graph));
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::graph::model::{Graph, GraphError};
    use crate::graph::vmodel::*;
    use std::collections::BTreeMap;

    /// Test-only helper (T-3044 H3): every `artifact`/`test` node fixture
    /// needs its required attr populated with SOMETHING to construct at
    /// all; this derives a stand-in value from the node's own id so each
    /// fixture stays readable without hand-typing a payload string per
    /// call site. Real callers put a real `path[:symbol]`/pytest node id
    /// here -- see `payload_construction_refuses_test_missing_runnable`
    /// and `payload_construction_refuses_artifact_missing_code_ref` below
    /// for the refusal behavior this helper's presence would otherwise mask.
    // frob:ticket T-3260
    fn attrs_with(key: &str, id: &str) -> BTreeMap<String, String> {
        BTreeMap::from([(key.to_string(), format!("fixture::{id}"))])
    }

    // Shared fixture builder: a two-node chain spanning the OUTERMOST
    // ("req-1", level requirements) and INNERMOST ("design-1", level
    // component-design) V-model levels, with design-1 satisfying req-1.
    // Using the two boundary levels (rather than two adjacent middle ones)
    // means req-1 is exempt from rule 2 (nothing above it to trace to) and
    // design-1 is exempt from rule 1 (nothing more detailed to satisfy it)
    // -- so this fixture is fully closed for rules 1-2 with no further
    // nodes needed; tests add verifying tests at each node's OWN paired
    // level as needed for rules 3-4.
    // frob:ticket T-3260
    fn base_graph() -> Graph {
        let mut g = Graph::new(v_model_schema());
        g.add_node_with_attrs(
            "req-1",
            KIND_ARTIFACT,
            Some(LEVEL_REQUIREMENTS.into()),
            attrs_with(ATTR_CODE_REF, "req-1"),
        )
        .unwrap();
        g.add_node_with_attrs(
            "design-1",
            KIND_ARTIFACT,
            Some(LEVEL_COMPONENT_DESIGN.into()),
            attrs_with(ATTR_CODE_REF, "design-1"),
        )
        .unwrap();
        g.add_edge(EDGE_SATISFIES, "design-1", "req-1").unwrap();
        g
    }

    #[test]
    // frob:ticket T-3007
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_orphan_requirements kind="unit"
    // frob:ticket T-3260
    fn rule1_must_fire_on_orphan_requirement() {
        let mut g = Graph::new(v_model_schema());
        // A requirement with nothing satisfying it.
        g.add_node_with_attrs(
            "lonely-req",
            KIND_ARTIFACT,
            Some(LEVEL_REQUIREMENTS.into()),
            attrs_with(ATTR_CODE_REF, "lonely-req"),
        )
        .unwrap();
        let violations = check_no_orphan_requirements(&g);
        assert_eq!(
            violations,
            vec![ClosureViolation::OrphanRequirement {
                node: "lonely-req".into()
            }]
        );
    }

    #[test]
    // frob:ticket T-3007
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_orphan_requirements kind="unit"
    // frob:ticket T-3260
    fn rule1_must_stay_quiet_when_satisfied() {
        let g = base_graph();
        assert!(check_no_orphan_requirements(&g).is_empty());
    }

    #[test]
    // frob:ticket T-3007
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_unjustified_design kind="unit"
    // frob:ticket T-3260
    fn rule2_must_fire_on_unjustified_design() {
        let mut g = base_graph();
        // A design element tracing to nothing -- unjustified code.
        g.add_node_with_attrs(
            "dangling-design",
            KIND_ARTIFACT,
            Some(LEVEL_COMPONENT_DESIGN.into()),
            attrs_with(ATTR_CODE_REF, "dangling-design"),
        )
        .unwrap();
        let violations = check_no_unjustified_design(&g);
        assert_eq!(
            violations,
            vec![ClosureViolation::UnjustifiedDesign {
                node: "dangling-design".into()
            }]
        );
    }

    #[test]
    // frob:ticket T-3007
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_unjustified_design kind="unit"
    // frob:ticket T-3260
    fn rule2_must_stay_quiet_when_traced() {
        let g = base_graph();
        // req-1 is a root requirement (no expectation it traces further);
        // reqspec-1 traces via `satisfies` to req-1.
        assert!(check_no_unjustified_design(&g).is_empty());
    }

    #[test]
    // frob:ticket T-3007
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_untested_artifact kind="unit"
    // frob:ticket T-3260
    fn rule3_must_fire_on_untested_requirement() {
        let g = base_graph();
        // req-1 and design-1 both exist; neither has any verifying test.
        let violations = check_no_untested_artifact(&g);
        assert_eq!(violations.len(), 2);
        assert!(violations.contains(&ClosureViolation::UntestedArtifact {
            node: "req-1".into()
        }));
        assert!(violations.contains(&ClosureViolation::UntestedArtifact {
            node: "design-1".into()
        }));
    }

    #[test]
    // frob:ticket T-3007
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_untested_artifact kind="unit"
    // frob:ticket T-3260
    fn rule3_must_stay_quiet_when_verified_at_paired_level() {
        let mut g = base_graph();
        g.add_node_with_attrs(
            "ctest-1",
            KIND_TEST,
            Some(LEVEL_CUSTOMER_TEST.into()),
            attrs_with(ATTR_RUNNABLE, "ctest-1"),
        )
        .unwrap();
        g.add_edge(EDGE_VERIFIES, "ctest-1", "req-1").unwrap();
        g.add_node_with_attrs(
            "unittest-1",
            KIND_TEST,
            Some(LEVEL_COMPONENT_UNIT_TEST.into()),
            attrs_with(ATTR_RUNNABLE, "unittest-1"),
        )
        .unwrap();
        g.add_edge(EDGE_VERIFIES, "unittest-1", "design-1").unwrap();
        assert!(check_no_untested_artifact(&g).is_empty());
    }

    #[test]
    // frob:ticket T-3007
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_untested_artifact kind="unit"
    // frob:ticket T-3260
    fn rule3_wrong_level_test_is_refused_at_construction_not_silently_accepted() {
        // A customer-test (paired to `requirements`) cannot verify
        // `design-1` (paired to `component-design`) -- the kernel's
        // LevelConstraintViolation catches this before rule 3 ever runs,
        // so rule 3 still correctly reports design-1 untested.
        let mut g = base_graph();
        g.add_node_with_attrs(
            "ctest-1",
            KIND_TEST,
            Some(LEVEL_CUSTOMER_TEST.into()),
            attrs_with(ATTR_RUNNABLE, "ctest-1"),
        )
        .unwrap();
        let err = g
            .add_edge(EDGE_VERIFIES, "ctest-1", "design-1")
            .unwrap_err();
        assert!(matches!(err, GraphError::LevelConstraintViolation { .. }));
        let violations = check_no_untested_artifact(&g);
        assert!(violations.contains(&ClosureViolation::UntestedArtifact {
            node: "design-1".into()
        }));
    }

    #[test]
    // frob:ticket T-3007
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_orphan_test kind="unit"
    // frob:ticket T-3260
    fn rule4_must_fire_on_orphan_test() {
        let mut g = base_graph();
        g.add_node_with_attrs(
            "stray-test",
            KIND_TEST,
            Some(LEVEL_CUSTOMER_TEST.into()),
            attrs_with(ATTR_RUNNABLE, "stray-test"),
        )
        .unwrap();
        let violations = check_no_orphan_test(&g);
        assert_eq!(
            violations,
            vec![ClosureViolation::OrphanTest {
                node: "stray-test".into()
            }]
        );
    }

    #[test]
    // frob:ticket T-3007
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_orphan_test kind="unit"
    // frob:ticket T-3260
    fn rule4_must_stay_quiet_when_verifying_something() {
        let mut g = base_graph();
        g.add_node_with_attrs(
            "ctest-1",
            KIND_TEST,
            Some(LEVEL_CUSTOMER_TEST.into()),
            attrs_with(ATTR_RUNNABLE, "ctest-1"),
        )
        .unwrap();
        g.add_edge(EDGE_VERIFIES, "ctest-1", "req-1").unwrap();
        assert!(check_no_orphan_test(&g).is_empty());
    }

    #[test]
    // frob:ticket T-3007
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_closure kind="unit"
    // frob:ticket T-3260
    fn check_closure_is_empty_on_a_fully_closed_two_level_graph() {
        let mut g = base_graph();
        g.add_node_with_attrs(
            "ctest-1",
            KIND_TEST,
            Some(LEVEL_CUSTOMER_TEST.into()),
            attrs_with(ATTR_RUNNABLE, "ctest-1"),
        )
        .unwrap();
        g.add_edge(EDGE_VERIFIES, "ctest-1", "req-1").unwrap();
        g.add_node_with_attrs(
            "unittest-1",
            KIND_TEST,
            Some(LEVEL_COMPONENT_UNIT_TEST.into()),
            attrs_with(ATTR_RUNNABLE, "unittest-1"),
        )
        .unwrap();
        g.add_edge(EDGE_VERIFIES, "unittest-1", "design-1").unwrap();
        assert!(check_closure(&g).is_empty());
    }

    #[test]
    // frob:ticket T-3043
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_orphan_requirements kind="unit"
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_unjustified_design kind="unit"
    // frob:ticket T-3260
    fn h2_mutual_satisfies_pair_with_zero_requirements_now_fires() {
        // T-3043 H2's exact escape: two system-design artifacts pointing
        // at each other via `satisfies`, each verified by a test at its
        // own paired level, and NO requirements-level node anywhere in
        // the graph. Under the OLD "non-empty closure" check this passed
        // all four rules; it must now fire rules 1 and 2, because neither
        // A nor B's satisfies-closure ever reaches a real requirement (or,
        // symmetrically, a real grounded design).
        let mut g = Graph::new(v_model_schema());
        g.add_node_with_attrs(
            "design-a",
            KIND_ARTIFACT,
            Some(LEVEL_SYSTEM_DESIGN.into()),
            attrs_with(ATTR_CODE_REF, "design-a"),
        )
        .unwrap();
        g.add_node_with_attrs(
            "design-b",
            KIND_ARTIFACT,
            Some(LEVEL_SYSTEM_DESIGN.into()),
            attrs_with(ATTR_CODE_REF, "design-b"),
        )
        .unwrap();
        g.add_edge(EDGE_SATISFIES, "design-a", "design-b").unwrap();
        g.add_edge(EDGE_SATISFIES, "design-b", "design-a").unwrap();
        g.add_node_with_attrs(
            "itest-a",
            KIND_TEST,
            Some(LEVEL_SUBSYSTEM_INTEGRATION_TEST_PLAN.into()),
            attrs_with(ATTR_RUNNABLE, "itest-a"),
        )
        .unwrap();
        g.add_edge(EDGE_VERIFIES, "itest-a", "design-a").unwrap();
        g.add_node_with_attrs(
            "itest-b",
            KIND_TEST,
            Some(LEVEL_SUBSYSTEM_INTEGRATION_TEST_PLAN.into()),
            attrs_with(ATTR_RUNNABLE, "itest-b"),
        )
        .unwrap();
        g.add_edge(EDGE_VERIFIES, "itest-b", "design-b").unwrap();

        // Rules 3/4 (verifies-based) are satisfied by construction here --
        // this fixture isolates rules 1/2's path-closure hole, not the
        // verifies-pairing behavior those two rules already got right.
        assert!(check_no_untested_artifact(&g).is_empty());
        assert!(check_no_orphan_test(&g).is_empty());

        let orphan_req = check_no_orphan_requirements(&g);
        assert_eq!(
            orphan_req.len(),
            2,
            "both design-a and design-b are unrooted: {orphan_req:?}"
        );
        assert!(orphan_req.contains(&ClosureViolation::OrphanRequirement {
            node: "design-a".into()
        }));
        assert!(orphan_req.contains(&ClosureViolation::OrphanRequirement {
            node: "design-b".into()
        }));

        let unjustified = check_no_unjustified_design(&g);
        assert_eq!(
            unjustified.len(),
            2,
            "neither traces to a real requirement: {unjustified:?}"
        );
        assert!(unjustified.contains(&ClosureViolation::UnjustifiedDesign {
            node: "design-a".into()
        }));
        assert!(unjustified.contains(&ClosureViolation::UnjustifiedDesign {
            node: "design-b".into()
        }));

        // And the top-level entry point must see it too.
        let violations = check_closure(&g);
        assert!(violations.contains(&ClosureViolation::OrphanRequirement {
            node: "design-a".into()
        }));
        assert!(violations.contains(&ClosureViolation::UnjustifiedDesign {
            node: "design-a".into()
        }));
    }

    #[test]
    // frob:ticket T-3043
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_orphan_requirements kind="unit"
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_unjustified_design kind="unit"
    // frob:ticket T-3260
    fn h2_genuine_four_level_chain_stays_quiet() {
        // The positive control for the H2 fix: a real chain from a
        // requirement all the way down to a component design, verified at
        // EACH paired level, must still pass -- the fix must not overtighten
        // and start rejecting legitimate multi-hop traces.
        let mut g = Graph::new(v_model_schema());
        g.add_node_with_attrs(
            "req-1",
            KIND_ARTIFACT,
            Some(LEVEL_REQUIREMENTS.into()),
            attrs_with(ATTR_CODE_REF, "req-1"),
        )
        .unwrap();
        g.add_node_with_attrs(
            "spec-1",
            KIND_ARTIFACT,
            Some(LEVEL_REQUIREMENT_SPEC.into()),
            attrs_with(ATTR_CODE_REF, "spec-1"),
        )
        .unwrap();
        g.add_node_with_attrs(
            "design-1",
            KIND_ARTIFACT,
            Some(LEVEL_SYSTEM_DESIGN.into()),
            attrs_with(ATTR_CODE_REF, "design-1"),
        )
        .unwrap();
        g.add_node_with_attrs(
            "component-1",
            KIND_ARTIFACT,
            Some(LEVEL_COMPONENT_DESIGN.into()),
            attrs_with(ATTR_CODE_REF, "component-1"),
        )
        .unwrap();
        g.add_edge(EDGE_SATISFIES, "spec-1", "req-1").unwrap();
        g.add_edge(EDGE_SATISFIES, "design-1", "spec-1").unwrap();
        g.add_edge(EDGE_SATISFIES, "component-1", "design-1")
            .unwrap();

        g.add_node_with_attrs(
            "ctest-1",
            KIND_TEST,
            Some(LEVEL_CUSTOMER_TEST.into()),
            attrs_with(ATTR_RUNNABLE, "ctest-1"),
        )
        .unwrap();
        g.add_edge(EDGE_VERIFIES, "ctest-1", "req-1").unwrap();
        g.add_node_with_attrs(
            "ctp-1",
            KIND_TEST,
            Some(LEVEL_CUSTOMER_TEST_PLAN.into()),
            attrs_with(ATTR_RUNNABLE, "ctp-1"),
        )
        .unwrap();
        g.add_edge(EDGE_VERIFIES, "ctp-1", "spec-1").unwrap();
        g.add_node_with_attrs(
            "sitp-1",
            KIND_TEST,
            Some(LEVEL_SUBSYSTEM_INTEGRATION_TEST_PLAN.into()),
            attrs_with(ATTR_RUNNABLE, "sitp-1"),
        )
        .unwrap();
        g.add_edge(EDGE_VERIFIES, "sitp-1", "design-1").unwrap();
        g.add_node_with_attrs(
            "unittest-1",
            KIND_TEST,
            Some(LEVEL_COMPONENT_UNIT_TEST.into()),
            attrs_with(ATTR_RUNNABLE, "unittest-1"),
        )
        .unwrap();
        g.add_edge(EDGE_VERIFIES, "unittest-1", "component-1")
            .unwrap();

        assert!(check_closure(&g).is_empty(), "{:?}", check_closure(&g));
    }

    #[test]
    // frob:ticket T-3043
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_trace_cycle kind="unit"
    // frob:ticket T-3260
    fn rule5_must_fire_on_a_satisfies_cycle_via_check_closure() {
        // T-3043 H2's second finding: find_cycle existed in the kernel but
        // nothing in check_closure ever called it. This plants a genuine
        // cycle in the trace subgraph and asserts it fires THROUGH
        // check_closure, not merely via a direct find_cycle call.
        let mut g = Graph::new(v_model_schema());
        g.add_node_with_attrs(
            "a",
            KIND_ARTIFACT,
            Some(LEVEL_SYSTEM_DESIGN.into()),
            attrs_with(ATTR_CODE_REF, "a"),
        )
        .unwrap();
        g.add_node_with_attrs(
            "b",
            KIND_ARTIFACT,
            Some(LEVEL_SYSTEM_DESIGN.into()),
            attrs_with(ATTR_CODE_REF, "b"),
        )
        .unwrap();
        g.add_node_with_attrs(
            "c",
            KIND_ARTIFACT,
            Some(LEVEL_SYSTEM_DESIGN.into()),
            attrs_with(ATTR_CODE_REF, "c"),
        )
        .unwrap();
        g.add_edge(EDGE_SATISFIES, "a", "b").unwrap();
        g.add_edge(EDGE_SATISFIES, "b", "c").unwrap();
        g.add_edge(EDGE_SATISFIES, "c", "a").unwrap();

        let direct = check_no_trace_cycle(&g);
        assert_eq!(direct.len(), 1);
        assert!(matches!(&direct[0], ClosureViolation::TraceCycle { cycle } if !cycle.is_empty()));

        let violations = check_closure(&g);
        assert!(
            violations
                .iter()
                .any(|v| matches!(v, ClosureViolation::TraceCycle { .. })),
            "check_closure must surface the cycle, not just check_no_trace_cycle directly: {violations:?}"
        );
    }

    #[test]
    // frob:ticket T-3043
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_no_trace_cycle kind="unit"
    // frob:ticket T-3260
    fn rule5_stays_quiet_on_the_genuine_chain() {
        // Must-quiet twin over the SAME node layout as the fire case above
        // minus the closing edge, per the positive-control lesson.
        let g = base_graph();
        assert!(check_no_trace_cycle(&g).is_empty());
    }

    #[test]
    // frob:ticket T-3007
    // frob:tests strata-core/src/graph/vmodel/closure.rs::check_closure kind="unit"
    // frob:ticket T-3260
    fn check_closure_reports_all_four_rules_on_a_maximally_broken_graph() {
        let mut g = Graph::new(v_model_schema());
        g.add_node_with_attrs(
            "lonely-req",
            KIND_ARTIFACT,
            Some(LEVEL_REQUIREMENTS.into()),
            attrs_with(ATTR_CODE_REF, "lonely-req"),
        )
        .unwrap();
        g.add_node_with_attrs(
            "dangling-design",
            KIND_ARTIFACT,
            Some(LEVEL_COMPONENT_DESIGN.into()),
            attrs_with(ATTR_CODE_REF, "dangling-design"),
        )
        .unwrap();
        g.add_node_with_attrs(
            "stray-test",
            KIND_TEST,
            Some(LEVEL_CUSTOMER_TEST.into()),
            attrs_with(ATTR_RUNNABLE, "stray-test"),
        )
        .unwrap();
        let violations = check_closure(&g);
        assert!(violations.contains(&ClosureViolation::OrphanRequirement {
            node: "lonely-req".into()
        }));
        assert!(violations.contains(&ClosureViolation::UnjustifiedDesign {
            node: "dangling-design".into()
        }));
        assert!(violations.contains(&ClosureViolation::UntestedArtifact {
            node: "lonely-req".into()
        }));
        assert!(violations.contains(&ClosureViolation::OrphanTest {
            node: "stray-test".into()
        }));
    }
}
