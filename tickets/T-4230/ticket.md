---
id: T-4230
title: 'entrypoint coverage: a module''s __main__ guard is not a symbol, so TEST/COV
  gates never see whether the CLI entry path itself is exercised'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: high
parent: T-4175
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_coverage.py
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
Consumer F-373/P7 (T-4175): every existing test for a module imports it in-process under pytest, where the repo root is already on sys.path -- so the one thing that is broken (the CLI entry point) is the one thing no test uses. build_app, schema, render, main are all covered; the __main__ guard is not a symbol these gates measure. High-value, directly applicable to frob's own CLI. Fixture-testable: YES, frob's own __main__ entrypoints.