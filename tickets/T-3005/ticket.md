---
id: T-3005
title: 'strata-core graph kernel: generic typed nodes, typed edges, closure, level
  constraints, cycle detection (see T-3004 section 4)'
state: queued
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: T-3004
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/graph/**
- strata-core/src/lib.rs
- strata-core/Cargo.toml
- docs/strata/graph.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: strata-core/src/graph/**
  reason: new graph kernel module beside parse, plus pyo3 wiring in lib.rs
  actor: logan
  at: '2026-08-26'
- op: add
  glob: strata-core/src/lib.rs
  reason: new graph kernel module beside parse, plus pyo3 wiring in lib.rs
  actor: logan
  at: '2026-08-26'
- op: add
  glob: strata-core/Cargo.toml
  reason: new graph kernel module beside parse, plus pyo3 wiring in lib.rs
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/strata/graph.md
  reason: kernel doc for new graph module
  actor: logan
  at: '2026-08-26'
triage_changes:
- field: parent
  old_value: null
  new_value: T-3004
  reason: T-3004 decomposition per the owner design decision
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
