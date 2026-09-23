---
id: T-5292
title: TICK008 flags real ledger branch/worktree fields it itself wrote
state: queued
kind: bug
origin: human
created: '2026-09-22'
priority: medium
blocked_by:
- T-5305
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
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
- tests/gates_suite/test_tick.py
- src/frob/gates/_tickets_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates
  reason: narrow off gates/__init__.py to avoid T-5267 lease collision; TICK008 lives
    in _tickets_gate.py
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: narrow off gates/__init__.py to avoid T-5267 lease collision; TICK008 lives
    in _tickets_gate.py
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5292
branch: t-5292
---
gh run 35717833933 ubuntu Test job; re-verified on dev tip 3acf8c6b30: tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean fails -- ~35 real tickets carry unknown ledger field(s) ['branch','worktree'], gate treats as TICK008 violation on the live repo ledger itself.