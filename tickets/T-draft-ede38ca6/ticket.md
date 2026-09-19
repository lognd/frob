---
id: T-draft-ede38ca6
title: land Tier-A directive canonicalizer emits lines over the ruff limit that the
  land's own ruff gate then refuses (E501), self-refusing every ticket whose frob:doc
  anchor is long
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine.py
- tests/gates_suite/test_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: fix _rewrite_line_substring to noqa-guard a rewrite that pushes a directive
    line over the ruff limit
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/gates_suite/test_fix_engine.py
  reason: 'positive control: a directive that expands past 88 chars survives Tier-A
    and ruff'
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
