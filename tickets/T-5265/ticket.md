---
id: T-5265
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-4599):
  3 new (rule, file) identit(ies), 51 finding(s) (DUP001, DUP002, PERF002)'
state: queued
kind: bug
origin: agent
created: '2026-09-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
- tests/gates_suite/test_tick_dead_worktree.py
findings:
- - DUP001
  - tests/gates_suite/test_tick_dead_worktree.py
- - DUP002
  - tests/gates_suite/test_tick_dead_worktree.py
- - PERF002
  - src/frob/gates/_tickets_gate.py
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-4599) at commit e2e82796072ac3216f72e05f47dda88df4542ed6 found 7 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (3), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 51 actual finding(s) across those 3 identit(ies).

New (rule, file) identit(ies) filed here:

- DUP001  tests/gates_suite/test_tick_dead_worktree.py
- DUP002  tests/gates_suite/test_tick_dead_worktree.py
- PERF002  src/frob/gates/_tickets_gate.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV002  src/frob/gates/_tickets_gate.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['7abb39bb3f1e3d4c8cdadb7f12dcd9f960837d5d', '7a296451e634888e7c7e82a80cf25de3b87e7071']
- DOC012  docs/commands/  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP001  tests/gates_suite/test_tick_dead_worktree.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP002  tests/gates_suite/test_tick_dead_worktree.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF002  src/frob/gates/_tickets_gate.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['7abb39bb3f1e3d4c8cdadb7f12dcd9f960837d5d', '7a296451e634888e7c7e82a80cf25de3b87e7071']
- TEST009  design/frob.strata  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK015  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.