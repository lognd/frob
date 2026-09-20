---
id: T-5092
title: 'cli-regrouping: ops natives group leaf missing --path (parity drift)'
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: v0.537.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_cli_group_parity.py
- src/frob/_cli_parsers/_ops.py
- src/frob/_cli_parsers/_misc.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ops.py
  reason: mirror --path onto the ops-group natives leaf
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: reference flat natives parser for the --path mirror pattern; may extract
    shared helper
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: src/frob/_cli_parsers/**
  reason: narrow to the two files that actually need the fix; ** collided with T-3995's
    lease on _check.py
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.537.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: GIVEN the ops-group natives leaf WHEN its option strings are compared to the
    flat natives parser's THEN they are identical (including --path)
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35448990233 (dev tip beedd71c4) failed all 3 platforms: tests/unit/test_cli_group_parity.py::TestOpsGroupParity::test_every_ops_leaf_matches_its_flat_twin[natives]. frob ops natives option strings {--help,-h} vs frob natives {--help,--path,-h}. The group-parser generator (T-4520) is not copying every flat-parser option onto the generated leaf. Fix generator + add a parity drift-lock test. Repro: tests/unit/test_cli_group_parity.py::TestOpsGroupParity::test_every_ops_leaf_matches_its_flat_twin[natives]

## Failure log
- 2026-09-20 attempt 1: coordinator: in-progress with no worktree or branch carrying work; requeued for a fresh agent
