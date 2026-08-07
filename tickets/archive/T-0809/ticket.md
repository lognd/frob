---
id: T-0809
title: wire real callee-resolution + resource-tracking DSL into the T-0745 protocol
  summary engine
state: done
kind: feature
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/graph/dsl.py
- docs/modules/graph.md
- tests/test_graph.py
- tests/unit/test_arch.py
- tests/unit/graph/test_dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_graph.py
  reason: 'Deterministic fixture tests for the two T-0809 mechanisms (real

    callee-resolution UNRESOLVED_CALLEE wiring in build_call_graph, and the

    new resource-tracking DSL folded into compute_protocol_summaries) live in

    the existing test homes for the modules they exercise, per the playbook''s

    evidence discipline: tests/test_graph.py already hosts TestCallGraph

    (build_call_graph/build_reference_graph fixture tests) and

    tests/unit/test_arch.py already hosts TestProtocolSummaryEngine (the

    T-0745 summary-engine fixture tests this ticket extends) -- adding a

    parallel, disconnected test file for the same two modules would just be

    duplication.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_arch.py
  reason: 'Deterministic fixture tests for the two T-0809 mechanisms (real

    callee-resolution UNRESOLVED_CALLEE wiring in build_call_graph, and the

    new resource-tracking DSL folded into compute_protocol_summaries) live in

    the existing test homes for the modules they exercise, per the playbook''s

    evidence discipline: tests/test_graph.py already hosts TestCallGraph

    (build_call_graph/build_reference_graph fixture tests) and

    tests/unit/test_arch.py already hosts TestProtocolSummaryEngine (the

    T-0745 summary-engine fixture tests this ticket extends) -- adding a

    parallel, disconnected test file for the same two modules would just be

    duplication.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: 'tests/unit/graph/test_dsl.py is dsl.py''s own dedicated parser test home

    (TestProtocolDeclarations already covers the T-0744 protocol/transition/

    requires verbs this ticket''s resource verbs are siblings of) -- the

    correct place for a directive-grammar round-trip test, not

    tests/test_graph.py or tests/unit/test_arch.py (which cover the summary

    engine''s join semantics, already scoped).

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_graph.py::TestCallGraph::test_build_call_graph_marks_unresolved_private_looking_callee
- tests/test_graph.py::TestCallGraph::test_build_call_graph_does_not_mark_unresolved_public_looking_call
- tests/test_graph.py::TestCallGraph::test_build_call_graph_default_preserves_old_silent_omission_behavior
- tests/test_graph.py::TestCallGraph::test_build_call_graph_resolved_private_callee_is_not_also_unresolved
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_resource_declarations_populate_acquired_released_escaped
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_resource_sets_join_transitively_through_a_caller
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_resource_sets_join_across_a_recursive_cluster
- tests/unit/graph/test_dsl.py::TestResourceDirectives::test_acquire_release_escapes_round_trip
- tests/unit/graph/test_dsl.py::TestResourceDirectives::test_acquire_missing_target_is_malformed
designated_repro_test: null
threat: null
component: null
---
T-0745 built the shared per-function protocol-summary fixpoint engine
(frob.graph.summary.compute_protocol_summaries) over an explicit
CallGraph + Edge input, with UNRESOLVED_CALLEE as an engine-level sentinel
a caller wires in to mean "this call could not be bound". Two pieces of
the original design sketch were explicitly deferred, not built:

1. Real callee-resolution wiring: nothing yet decides, from real source,
   when a call site should become UNRESOLVED_CALLEE in the CallGraph fed
   to the engine (the ticket referenced "T-0339-family resolvers for
   callee binding" for this). frob.graph.callgraph.build_call_graph today
   silently omits any call it cannot resolve rather than recording it as
   unresolved -- that gap needs closing before the engine's poisoning
   channel means anything on a real repo scan, not just fixture graphs.

2. The "acquired/released/escaped resources" third of the summary
   (states/transitions are covered; resources are not) -- there is no
   frob:acquire/frob:release-style DSL surface for this yet, only the
   T-0744 protocol/transition/requires directives.

Also noted: the T-0745 ticket's own DESIGN CONSTRAINT ("ONE engine shared
with T-0686 may-raise, whichever builds first hosts it") could not be
coordinated on this pass -- T-0686 does not exist yet. Whoever builds
T-0686 should consume frob.graph.summary's SCC/fixpoint machinery rather
than re-deriving a second one.