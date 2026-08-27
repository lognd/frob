---
id: T-3078
title: 'TEST001 gap: T-3044''s new graph::model attrs API has no bound unit test'
state: queued
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
- strata-core/src/graph/model.rs
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

T-3044 (V-model H3, landed as commit 51bc8c6ddb492d00af3341e00f7727011e8a961c)
added several new public symbols to strata-core/src/graph/model.rs:

- EdgeKindSchema::require_attrs
- GraphSchema::declare_required_node_attrs
- Graph::add_node_with_attrs
- Graph::add_edge_with_attrs

All four are exercised extensively (indirectly, through v_model_schema()
and every graph::vmodel test fixture), but none has an explicit
frob:tests directive or a convention-matched test function name, so
`frob check --only test` reports TEST001 for each of them on main.

## Plan

Add a frob:tests directive (or a dedicated test_<symbol> unit test) for
each of the four T-3044 symbols above, pointing at whichever existing
test already exercises it.

## Acceptance criteria

1. `frob check --only test` reports zero TEST001 findings for
   EdgeKindSchema.require_attrs, GraphSchema.declare_required_node_attrs,
   Graph.add_node_with_attrs, Graph.add_edge_with_attrs.
