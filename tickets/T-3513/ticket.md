---
id: T-3513
title: Wire zig into vet/dup/docblock capability facets
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 1.0.0
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
- src/frob/vet/_capability_registry/**
- src/frob/dup/_exhaustiveness.py
- src/frob/gates/_docblocks.py
- src/frob/lang/_support.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.532.0
  new_value: backlog
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-15'
- field: milestone
  old_value: v0.532.0
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-15'
- field: sprint
  old_value: backlog
  new_value: v0.541.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-1603: zig gets a real frob.lang grammar/walker but the capability dangerous-op registry, dup clone-detection exhaustiveness table, and DOC004 fenced-code-block bucket have no zig entry yet -- mirrors T-2906's bash/csharp, T-1601's java, and T-1602's cuda facet-wiring follow-ups exactly (T-3492, T-3493). frob.lang._support marks these three facets KNOWN_GAP for zig citing this ticket in the interim.