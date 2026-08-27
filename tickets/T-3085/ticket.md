---
id: T-3085
title: 'post-land sweep regression from T-3065, T-3039, T-3060: 1 new (rule, file)
  identit(ies), 0 finding(s) (I001)'
state: done
kind: bug
origin: agent
created: '2026-08-27'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/verify/test_quarantine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'mark as no-behavior-change: lint-only fix'
  actor: logan
  at: '2026-08-27'
  old_length: 1793
  new_length: 177
evidence:
- tests/unit/verify/test_quarantine.py::TestNormalizeFindingPath::test_absolute_and_relative_resolve_identical
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:no-behavior-change reason="pure import-sort reordering (I001 autofix), no behavior change; the bound test proves the import block still resolves correctly, not a bug-repro"