---
id: T-5474
title: 'cli_group_parity: frob ops natives missing --path option present on flat twin'
state: done
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ops.py
- tests/unit/test_cli_group_parity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ops.py
  reason: add missing --path mirror to frob ops natives group parser
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_cli_group_parity.py
  reason: add missing --path mirror to frob ops natives group parser
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/test_cli_group_parity.py::TestOpsGroupParity::test_every_ops_leaf_matches_its_flat_twin[natives]
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5474
branch: t-5474
---
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/unit/test_cli_group_parity.py::TestOpsGroupParity::test_every_ops_leaf_matches_its_flat_twin[natives]

The grouped CLI surface (frob ops natives) and its flat twin (frob
natives) have diverged: {'--help', '-h'} vs {'--help', '--path', '-h'} --
the flat twin has a --path option the grouped twin is missing.

Fix: add the missing --path option to the grouped (frob ops natives) CLI
definition so both surfaces match again -- contained CLI-wiring fix, in
touch-scope.