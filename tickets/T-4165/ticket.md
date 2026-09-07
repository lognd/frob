---
id: T-4165
title: 'frob.gates: unify gate registration into a single GateSpec registry'
state: queued
kind: feature
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- src/frob/check/__init__.py
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
found while working T-4163: a new gate (name + rule id) currently must reach SIX independently-maintained lists (_ALL_GATES, _CANONICAL_GATE_ORDER, _build_process_jobs, _CACHEABLE_PROCESS_GATES, _STAGE_GROUPS, _KNOWN_GATE_RULES) -- see docs/modules/gates.md#registering-a-new-gate-t-4163 for the full inventory and why T-4163 did not attempt this refactor. Propose a single GateSpec dataclass registry (name, rule ids, cacheable flag, stage group membership, job factory) that the six existing structures derive from as views, so a new gate can no longer be added incompletely. Large blast radius: _ALL_GATES alone has dozens of call sites across frob.gates/frob.check/frob.tickets.