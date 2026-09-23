---
id: T-4774
title: 'worker and mcp-server presets: the long-running-service shapes the scaffold
  cannot express today'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4773
parent: T-4757
tier: ticket
sprint: null
runs_last: false
milestone: 1.1.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/facets/worker-queue/**
- src/frob/scaffold/data/facets/mcp/**
- src/frob/scaffold/data/presets/worker.toml
- src/frob/scaffold/data/presets/mcp-server.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.537.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.537.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: Given the rendered worker, when it processes a task and receives a termination
    signal, then it shuts down through its clean exit path
  evidence: []
- text: Given a handler returning an error value, when the worker runs it, then the
    loop survives and the failure is logged with the task identity
  evidence: []
- text: Given a fixture tool registered without a schema, when the rendered MCP conformance
    test runs, then it fails
  evidence: []
- text: Given both presets, when frob check runs in the rendered trees, then it is
    clean
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Two further presets, both shapes the house style already has written down
and the scaffold cannot express.

1. worker: python plus app-service plus a worker-queue facet -- a long-
   running queue consumer or background service. The task model is a
   pydantic model, the handler contract returns a Result, shutdown is
   graceful, and liveness is a heartbeat. refs/python-app.md's call method
   returning a never-type and running an async loop is exactly this shape
   and is currently unrepresented by any type.
   data-pipeline is NOT a separate preset: it is a scheduler facet over this
   one, and the typed source and sink models are ordinary application code,
   not scaffold surface.

2. mcp-server: python plus app-service plus an mcp facet -- a tool
   registration table, stdio and HTTP transports, the tool-result Result to
   MCP error mapping, and a conformance test asserting every registered tool
   has a schema. This is for CONSUMERS, so it must not depend on any frob
   internals, even though frob's own MCP adapter proves the shape in house.

Positive controls:
1. the rendered worker processes a task and shuts down cleanly on a
   termination signal, asserted on the exit path rather than on a timeout;
2. a handler returning an error value does not kill the worker loop, and the
   failure is logged with the task identity;
3. the rendered MCP server's conformance test fails when a fixture tool is
   registered without a schema (the positive control on the conformance test
   itself);
4. frob check clean on both presets.
