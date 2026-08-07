---
id: T-0745
title: 'protocol summary engine: per-function fixpoint over the call graph, shared
  with may-raise'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0744
parent: T-0739
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- src/frob/graph/**
- tests/unit/test_arch.py
- docs/modules/graph.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/graph.md
  reason: 'T-0745''s declared scope omitted a docs file, but every new public symbol

    (compute_protocol_summaries, FunctionSummary, SCCTimeout, SummaryResult,

    UNRESOLVED_CALLEE) needs a frob:doc edge resolving to a real anchor

    (COV001). Adding docs/modules/graph.md#protocol-summary-engine via the

    sanctioned frob ticket scope mechanism rather than hand-editing scope.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_function_summary_is_its_own_declarations
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_caller_summary_includes_callee_transitions
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_requires_and_transitions_join_across_two_hops
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_recursive_cluster_converges_to_hand_computed_fixpoint
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_self_recursive_function_converges
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unresolved_callee_poisons_the_summary
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_poisoning_propagates_transitively_through_a_clean_caller
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unreachable_function_is_reported_not_analyzed_never_silent
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_non_converging_scc_is_reported_as_a_timeout_error_and_poisoned
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_diamond_shaped_calls_join_without_duplication_or_loss
designated_repro_test: null
acceptance:
- text: GIVEN a recursive call cluster with transitions WHEN the fixpoint runs THEN
    summaries converge and match hand-computed values; GIVEN an unresolvable callee
    THEN the summary is poisoned and surfaces as an ERROR downstream, never silence
  evidence:
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_function_summary_is_its_own_declarations
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_caller_summary_includes_callee_transitions
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_requires_and_transitions_join_across_two_hops
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_recursive_cluster_converges_to_hand_computed_fixpoint
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_self_recursive_function_converges
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unresolved_callee_poisons_the_summary
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_poisoning_propagates_transitively_through_a_clean_caller
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_unreachable_function_is_reported_not_analyzed_never_silent
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_non_converging_scc_is_reported_as_a_timeout_error_and_poisoned
  - tests/unit/test_arch.py::TestProtocolSummaryEngine::test_diamond_shaped_calls_join_without_duplication_or_loss
threat: null
component: null
---
Child 2 of T-0739. The shared per-function summary fixpoint engine over the call graph: each function summarizes to (required protocol states, may-perform transitions, acquired/released/escaped resources) computed bottom-up to fixpoint, recursion via lattice join, using the T-0339-family resolvers for callee binding. DESIGN CONSTRAINT: ONE engine shared with T-0686 may-raise (whichever builds first hosts the engine; the other consumes -- coordinate explicitly, no second fixpoint). NO-FAIL-SILENT (user mandate): an unresolvable callee contributes Unknown which POISONS the summary (poisoned summaries are ERRORS at verification unless waived with reason); a function outside the call graph (unreachable from any entrypoint) is reported as not-analyzed, never silently passed; engine timeouts/aborts are ERRORS naming the SCC that failed to converge.