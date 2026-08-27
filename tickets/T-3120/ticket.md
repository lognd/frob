---
id: T-3120
title: 'TEST001 gap: Graph::has_cycle in strata-core/src/graph/query.rs has no unit
  test'
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/graph/query.rs
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- strata-core/src/graph/query.rs::tests::has_cycle_true_on_a_planted_cycle
- strata-core/src/graph/query.rs::tests::has_cycle_false_on_an_acyclic_graph
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3078 (scope: strata-core/src/graph/model.rs only). frob check --only test reports TEST001 for strata-core/src/graph/query.rs::Graph.has_cycle -- no explicit frob:tests directive or convention-matched test name. Add a real unit test that directly calls has_cycle (e.g. a graph with a genuine cycle asserting true, and an acyclic graph asserting false), matching the pattern used for T-3078's model.rs coverage.