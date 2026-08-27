---
id: T-3062
title: 'Lint for waive-vs-debt misuse: flag a frob:waive whose reason is temporary
  (cites a ticket, until, pending, once X lands)'
state: in-progress
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- docs/modules/gates.md
- tests/test_waive_gate.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: WAIVE010 waive-vs-debt misuse lint (T-3062)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/gates.md
  reason: WAIVE010 waive-vs-debt misuse lint (T-3062)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_waive_gate.py
  reason: WAIVE010 waive-vs-debt misuse lint (T-3062)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/__init__.py
  reason: wire WAIVE010 into run_gates alongside WAIVE009 (T-3062)
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
