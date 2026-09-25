//! The V-model spec graph as a `graph::model` schema instance
//! (docs/strata/vmodel.md, T-3004 sections 1-2).
//!
//! WHY here, not in `graph::model`: the kernel is generic by design (T-3005)
//! and names no domain vocabulary. This module is the FIRST CONSUMER --
//! it supplies node kinds, levels, edge kinds, and the paired-level
//! relations that make the V pairing checkable. The four structural
//! closure rules that layer on top of the kernel's
//! `forward_closure`/`backward_closure` live in the `closure` submodule
//! (T-3260: split out of this file once it crossed the LARGE001
//! threshold) -- re-exported here so callers see one flat `vmodel::`
//! surface.
//! Nothing here reaches back into `model`/`query` to add spec-specific
//! knowledge to the kernel itself.
// frob:waive REF002 reason="this ticket's own module doc (docs/strata/vmodel.md) is the single \
// inbound reference by design -- T-3007 is the FIRST consumer of the generic graph kernel, so a \
// second independent consumer does not exist yet; T-3008/T-3009/T-3010 (siblings blocked on this \
// schema) are the intended second reference once they land"

use super::model::{EdgeKindSchema, GraphSchema, Level, LevelRelation};
use std::collections::BTreeMap;

mod closure;
pub use closure::{
    check_closure, check_milestone_closure, check_no_orphan_requirements, check_no_orphan_test,
    check_no_trace_cycle, check_no_unjustified_design, check_no_untested_artifact,
    ClosureViolation,
};

/// Required node-attr key on every `KIND_TEST` node (T-3044 H3): the
/// runnable evidence this test node BINDS TO, in the same
/// `path::Class.method` (or `path::function`) qualname form
/// `frob:tests`/pytest collection already use -- a test node is no longer
/// an id with nothing runnable behind it.
// frob:doc docs/strata/vmodel.md#nodeedge-payload-t-3044-h3
// frob:ticket T-3260
pub const ATTR_RUNNABLE: &str = "runnable";
/// Required node-attr key on every `KIND_ARTIFACT` node (T-3044 H3): the
/// code this artifact node BINDS TO -- a `path[:symbol]` reference into the
/// repo (e.g. `strata-core/src/graph/model.rs:Graph::add_node`, or a bare
/// path for an artifact that is a whole file/module rather than one
/// symbol). An artifact node is no longer an id binding to no code.
// frob:doc docs/strata/vmodel.md#nodeedge-payload-t-3044-h3
// frob:ticket T-3260
pub const ATTR_CODE_REF: &str = "code_ref";
/// Required edge-attr key on every `EDGE_SUPERSEDES` edge (T-3044 H3): the
/// change justification, free-text but MANDATORY -- construction refuses a
/// `supersedes` edge with no `reason`, same as T-3004 section 8 already
/// requires for `decides`-adjacent change records.
// frob:doc docs/strata/vmodel.md#nodeedge-payload-t-3044-h3
// frob:ticket T-3260
pub const ATTR_REASON: &str = "reason";
/// Required node-attr key on every `KIND_REVIEW` node (T-3047): the
/// reviewed commit's sha -- the review's provenance as DATA, not a PR
/// description a human has to go read.
// frob:doc docs/strata/vmodel.md#nodeedge-payload-t-3044-h3
// frob:ticket T-3047
pub const ATTR_COMMIT: &str = "commit";

/// Node kind: a left-side artifact at some V-model level (requirement,
/// spec, system design, component design, decision, ...).
// frob:doc docs/strata/vmodel.md#node-kinds
// frob:ticket T-3260
pub const KIND_ARTIFACT: &str = "artifact";
/// Node kind: a right-side verification artifact (customer test, test
/// plan, integration test, unit test, ...).
// frob:doc docs/strata/vmodel.md#node-kinds
// frob:ticket T-3260
pub const KIND_TEST: &str = "test";
/// Node kind: a decision record -- the target of a `decides`/`supersedes`
/// edge (T-3004 section 8: change justification is a typed edge, not
/// inline prose). T-3047: REQUIRES `ATTR_REASON` -- a decision with no
/// stated reason is not a decision record, it is an unexplained fact.
// frob:doc docs/strata/vmodel.md#node-kinds
// frob:ticket T-3260
// frob:ticket T-3047
pub const KIND_DECISION: &str = "decision";
/// Node kind: a type-checked code review record with provenance (T-3047,
/// T-3004 section 8's review/decision family) -- the reviewed commit is
/// data (`ATTR_COMMIT`), not prose in a PR description. REQUIRES both
/// `ATTR_COMMIT` (the reviewed commit sha) and `ATTR_REASON` (the verdict
/// rationale) -- same "declaration carries the claim" discipline
/// `ATTR_CODE_REF`/`ATTR_RUNNABLE` already enforce for `artifact`/`test`.
// frob:doc docs/strata/vmodel.md#node-kinds
// frob:ticket T-3047
pub const KIND_REVIEW: &str = "review";

/// Left-side V-model levels, outermost (customer-facing) first. Exposed so
/// callers building fixtures do not hand-type the strings.
// frob:doc docs/strata/vmodel.md#levels-the-v-pairing-t-3004-section-1
// frob:ticket T-3260
pub const LEVEL_REQUIREMENTS: &str = "requirements";
// frob:doc docs/strata/vmodel.md#levels-the-v-pairing-t-3004-section-1
// frob:ticket T-3260
pub const LEVEL_REQUIREMENT_SPEC: &str = "requirement-specification";
// frob:doc docs/strata/vmodel.md#levels-the-v-pairing-t-3004-section-1
// frob:ticket T-3260
pub const LEVEL_SYSTEM_SPEC: &str = "system-specification";
// frob:doc docs/strata/vmodel.md#levels-the-v-pairing-t-3004-section-1
// frob:ticket T-3260
pub const LEVEL_SYSTEM_DESIGN: &str = "system-design";
// frob:doc docs/strata/vmodel.md#levels-the-v-pairing-t-3004-section-1
// frob:ticket T-3260
pub const LEVEL_COMPONENT_DESIGN: &str = "component-design";

/// Right-side (paired) V-model levels, in the same outermost-first order as
/// their left-side counterparts above.
// frob:doc docs/strata/vmodel.md#levels-the-v-pairing-t-3004-section-1
// frob:ticket T-3260
pub const LEVEL_CUSTOMER_TEST: &str = "customer-test";
// frob:doc docs/strata/vmodel.md#levels-the-v-pairing-t-3004-section-1
// frob:ticket T-3260
pub const LEVEL_CUSTOMER_TEST_PLAN: &str = "customer-test-plan";
// frob:doc docs/strata/vmodel.md#levels-the-v-pairing-t-3004-section-1
// frob:ticket T-3260
pub const LEVEL_SYSTEM_INTEGRATION_TEST_PLAN: &str = "system-integration-test-plan";
// frob:doc docs/strata/vmodel.md#levels-the-v-pairing-t-3004-section-1
// frob:ticket T-3260
pub const LEVEL_SUBSYSTEM_INTEGRATION_TEST_PLAN: &str = "subsystem-integration-test-plan";
// frob:doc docs/strata/vmodel.md#levels-the-v-pairing-t-3004-section-1
// frob:ticket T-3260
pub const LEVEL_COMPONENT_UNIT_TEST: &str = "component-unit-test";

/// The five left-side levels paired with their right-side verification
/// level, in the order T-3004 section 1 states them.
// frob:doc docs/strata/vmodel.md#schema-assembly
// frob:ticket T-3260
// kind="unit"
pub fn v_pairing() -> Vec<(Level, Level)> {
    vec![
        (LEVEL_REQUIREMENTS.into(), LEVEL_CUSTOMER_TEST.into()),
        (
            LEVEL_REQUIREMENT_SPEC.into(),
            LEVEL_CUSTOMER_TEST_PLAN.into(),
        ),
        (
            LEVEL_SYSTEM_SPEC.into(),
            LEVEL_SYSTEM_INTEGRATION_TEST_PLAN.into(),
        ),
        (
            LEVEL_SYSTEM_DESIGN.into(),
            LEVEL_SUBSYSTEM_INTEGRATION_TEST_PLAN.into(),
        ),
        (
            LEVEL_COMPONENT_DESIGN.into(),
            LEVEL_COMPONENT_UNIT_TEST.into(),
        ),
    ]
}

/// Edge kind: a design element traces UP to the requirement it justifies
/// (design -> requirement). Closure rules 1/2 walk this edge kind.
// frob:doc docs/strata/vmodel.md#edge-kinds
// frob:ticket T-3260
pub const EDGE_SATISFIES: &str = "satisfies";
/// Edge kind: a test verifies a left-side artifact, AT THAT ARTIFACT'S
/// PAIRED LEVEL (test -> artifact). Closure rules 3/4 walk this edge kind.
// frob:doc docs/strata/vmodel.md#edge-kinds
// frob:ticket T-3260
pub const EDGE_VERIFIES: &str = "verifies";
/// Edge kind: an artifact refines a coarser one one level up
/// (finer -> coarser), e.g. requirement-specification -> requirements.
// frob:doc docs/strata/vmodel.md#edge-kinds
// frob:ticket T-3260
pub const EDGE_REFINES: &str = "refines";
/// Edge kind: a system-level artifact allocates responsibility to a
/// component-level one (system -> component).
// frob:doc docs/strata/vmodel.md#edge-kinds
// frob:ticket T-3260
pub const EDGE_ALLOCATES: &str = "allocates";
/// Edge kind: a decision record resolves an open question about an
/// artifact (decision -> artifact).
// frob:doc docs/strata/vmodel.md#edge-kinds
// frob:ticket T-3260
pub const EDGE_DECIDES: &str = "decides";
/// Edge kind: a decision or artifact supersedes an earlier one, carrying
/// the change justification T-3004 section 8 requires (new -> old).
// frob:doc docs/strata/vmodel.md#edge-kinds
// frob:ticket T-3260
pub const EDGE_SUPERSEDES: &str = "supersedes";
/// Edge kind: pure scheduling fact, NOT the organising relation
/// (T-3004 section 3) -- unconstrained on purpose.
// frob:doc docs/strata/vmodel.md#edge-kinds
// frob:ticket T-3260
pub const EDGE_BLOCKED_BY: &str = "blocked_by";

/// Build the V-model `GraphSchema`: node kinds `artifact`/`test`/`decision`,
/// the ten V-model levels (five paired left/right levels), and the six
/// semantic edge kinds plus `blocked_by`. `verifies` is the only edge kind
/// carrying a `LevelRelation::Paired` constraint -- that pairing map is
/// exactly T-3004 section 1's table, keyed by src (test) level ->
/// required dst (artifact) level, matching `graph::model`'s existing
/// `verifies` convention (test -> requirement direction).
// frob:doc docs/strata/vmodel.md#schema-assembly
// frob:ticket T-3260
// strata-core/src/graph/vmodel/mod.rs::tests.v_model_schema_declares_every_kind_level_and_edge_kind kind="unit"
// strata-core/src/graph/vmodel/mod.rs::tests.v_model_schema_declares_every_kind_level_and_edge_kind
// frob:tests \
// strata-core/src/graph/vmodel/mod.rs::tests.v_model_schema_declares_every_kind_level_and_edge_kind
pub fn v_model_schema() -> GraphSchema {
    let mut s = GraphSchema::new();
    s.declare_node_kind(KIND_ARTIFACT)
        .declare_node_kind(KIND_TEST)
        .declare_node_kind(KIND_DECISION)
        .declare_node_kind(KIND_REVIEW);
    // T-3044 H3: a node kind is not fully typed until construction refuses
    // one missing its payload -- `test` binds to something runnable,
    // `artifact` binds to real code. T-3047 (owner review, superseding the
    // prior "decision carries no required attr" note): `decision` now
    // REQUIRES `ATTR_REASON` -- a decision record with no stated reason is
    // an unexplained fact, not a decision; `review` REQUIRES both
    // `ATTR_COMMIT` (the reviewed commit) and `ATTR_REASON` (the verdict
    // rationale), its provenance as data. T-3049 still owns normalizing
    // the FULL decision/invariant/review-record shape (title/status/...)
    // as one canonical schema; this ticket only adds the one field each
    // kind cannot be meaningfully absent, the same minimal-required-attr
    // precedent `ATTR_CODE_REF`/`ATTR_RUNNABLE` already set.
    s.declare_required_node_attrs(KIND_TEST, [ATTR_RUNNABLE]);
    s.declare_required_node_attrs(KIND_ARTIFACT, [ATTR_CODE_REF]);
    s.declare_required_node_attrs(KIND_DECISION, [ATTR_REASON]);
    s.declare_required_node_attrs(KIND_REVIEW, [ATTR_COMMIT, ATTR_REASON]);

    let mut pairing: BTreeMap<Level, Level> = BTreeMap::new();
    for (left, right) in v_pairing() {
        s.declare_level(left.clone());
        s.declare_level(right.clone());
        pairing.insert(right, left);
    }

    s.declare_edge_kind(
        EDGE_SATISFIES,
        EdgeKindSchema {
            allowed_src_kinds: [KIND_ARTIFACT.to_string()].into(),
            allowed_dst_kinds: [KIND_ARTIFACT.to_string()].into(),
            level_relation: LevelRelation::Any,
            required_attrs: std::collections::BTreeSet::new(),
        },
    );
    s.declare_edge_kind(
        EDGE_VERIFIES,
        EdgeKindSchema {
            allowed_src_kinds: [KIND_TEST.to_string()].into(),
            allowed_dst_kinds: [KIND_ARTIFACT.to_string()].into(),
            level_relation: LevelRelation::Paired(pairing),
            required_attrs: std::collections::BTreeSet::new(),
        },
    );
    s.declare_edge_kind(
        EDGE_REFINES,
        EdgeKindSchema {
            allowed_src_kinds: [KIND_ARTIFACT.to_string()].into(),
            allowed_dst_kinds: [KIND_ARTIFACT.to_string()].into(),
            level_relation: LevelRelation::Any,
            required_attrs: std::collections::BTreeSet::new(),
        },
    );
    s.declare_edge_kind(
        EDGE_ALLOCATES,
        EdgeKindSchema {
            allowed_src_kinds: [KIND_ARTIFACT.to_string()].into(),
            allowed_dst_kinds: [KIND_ARTIFACT.to_string()].into(),
            level_relation: LevelRelation::Any,
            required_attrs: std::collections::BTreeSet::new(),
        },
    );
    s.declare_edge_kind(
        EDGE_DECIDES,
        EdgeKindSchema {
            // T-3047: a review record can also resolve a question about
            // an artifact (a review's verdict IS a decision about the
            // reviewed code), not only a standalone `decision` node.
            allowed_src_kinds: [KIND_DECISION.to_string(), KIND_REVIEW.to_string()].into(),
            allowed_dst_kinds: [KIND_ARTIFACT.to_string()].into(),
            level_relation: LevelRelation::Any,
            required_attrs: std::collections::BTreeSet::new(),
        },
    );
    s.declare_edge_kind(
        EDGE_SUPERSEDES,
        EdgeKindSchema::unconstrained().require_attrs([ATTR_REASON]),
    );
    s.declare_edge_kind(EDGE_BLOCKED_BY, EdgeKindSchema::unconstrained());
    s
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    // frob:ticket T-3007
    // frob:ticket T-3260
    // frob:tests strata-core/src/graph/vmodel/mod.rs::v_pairing \
    fn v_pairing_has_five_pairs_in_t3004_order() {
        let pairs = v_pairing();
        assert_eq!(
            pairs,
            vec![
                (
                    LEVEL_REQUIREMENTS.to_string(),
                    LEVEL_CUSTOMER_TEST.to_string()
                ),
                (
                    LEVEL_REQUIREMENT_SPEC.to_string(),
                    LEVEL_CUSTOMER_TEST_PLAN.to_string()
                ),
                (
                    LEVEL_SYSTEM_SPEC.to_string(),
                    LEVEL_SYSTEM_INTEGRATION_TEST_PLAN.to_string()
                ),
                (
                    LEVEL_SYSTEM_DESIGN.to_string(),
                    LEVEL_SUBSYSTEM_INTEGRATION_TEST_PLAN.to_string()
                ),
                (
                    LEVEL_COMPONENT_DESIGN.to_string(),
                    LEVEL_COMPONENT_UNIT_TEST.to_string()
                ),
            ]
        );
    }

    #[test]
    // frob:ticket T-3007
    // frob:ticket T-3260
    fn v_model_schema_declares_every_kind_level_and_edge_kind() {
        let s = v_model_schema();
        assert_eq!(
            s.node_kinds,
            std::collections::BTreeSet::from([
                KIND_ARTIFACT.to_string(),
                KIND_TEST.to_string(),
                KIND_DECISION.to_string(),
                KIND_REVIEW.to_string(),
            ])
        );
        assert_eq!(s.levels.len(), 10);
        for kind in [
            EDGE_SATISFIES,
            EDGE_VERIFIES,
            EDGE_REFINES,
            EDGE_ALLOCATES,
            EDGE_DECIDES,
            EDGE_SUPERSEDES,
            EDGE_BLOCKED_BY,
        ] {
            assert!(s.edge_kinds.contains_key(kind), "missing edge kind {kind}");
        }
        // `verifies` must carry the Paired relation -- this is what makes
        // the V pairing checkable at construction time, T-3004 section 1.
        assert!(matches!(
            s.edge_kinds.get(EDGE_VERIFIES).unwrap().level_relation,
            LevelRelation::Paired(_)
        ));
    }

    #[test]
    // frob:ticket T-3047
    fn decision_node_with_no_reason_fails_schema_validation() {
        use super::super::model::Graph;
        let mut g = Graph::new(v_model_schema());
        let err = g.add_node("decision-1", KIND_DECISION, None).unwrap_err();
        assert!(matches!(
            err,
            super::super::model::GraphError::MissingNodeAttr { .. }
        ));
    }

    #[test]
    // frob:ticket T-3047
    fn decision_node_with_a_reason_constructs() {
        use super::super::model::Graph;
        let mut g = Graph::new(v_model_schema());
        g.add_node_with_attrs(
            "decision-1",
            KIND_DECISION,
            None,
            attrs_with(ATTR_REASON, "because the old approach leaked memory"),
        )
        .unwrap();
    }

    #[test]
    // frob:ticket T-3047
    fn review_node_requires_commit_and_reason() {
        use super::super::model::Graph;
        let mut g = Graph::new(v_model_schema());
        let err = g.add_node("review-1", KIND_REVIEW, None).unwrap_err();
        assert!(matches!(
            err,
            super::super::model::GraphError::MissingNodeAttr { .. }
        ));
    }

    #[test]
    // frob:ticket T-3047
    fn supersedes_edge_with_a_reason_round_trips_through_the_graph() {
        // T-3047's tree positive control: a decision node superseding an
        // earlier one via a typed `supersedes` edge carrying a reason
        // must round-trip through parse -> graph -> query. Parse-time
        // round-trip is already covered by `grammar_vmodel.rs`'s own
        // fixtures (`vmodel_edge kind "supersedes" ... reason "...";`);
        // this exercises the GRAPH half directly: construction accepts a
        // reasoned edge, and it is queryable afterward.
        use super::super::model::Graph;
        use super::super::query::KindFilter;
        let mut g = Graph::new(v_model_schema());
        g.add_node_with_attrs(
            "old-decision",
            KIND_DECISION,
            None,
            attrs_with(ATTR_REASON, "original call"),
        )
        .unwrap();
        g.add_node_with_attrs(
            "new-decision",
            KIND_DECISION,
            None,
            attrs_with(ATTR_REASON, "supersedes original call"),
        )
        .unwrap();
        g.add_edge_with_attrs(
            EDGE_SUPERSEDES,
            "new-decision",
            "old-decision",
            attrs_with(ATTR_REASON, "the original call was wrong, here is why"),
        )
        .unwrap();

        let filter_set: std::collections::BTreeSet<String> = [EDGE_SUPERSEDES.to_string()].into();
        let filter = KindFilter::Only(&filter_set);
        let closure = g.forward_closure("new-decision", &filter);
        assert!(closure.contains("old-decision"));
    }

    /// Test-only helper mirroring `closure.rs::tests::attrs_with`.
    // frob:ticket T-3047
    fn attrs_with(key: &str, value: &str) -> BTreeMap<String, String> {
        BTreeMap::from([(key.to_string(), value.to_string())])
    }
}
