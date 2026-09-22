---
id: T-5121
title: 'TICK rule: requeue an in-progress ticket whose recorded worktree or branch
  is dead'
state: done
kind: bug
origin: human
created: '2026-09-20'
priority: high
blocked_by:
- T-5120
parent: T-4651
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
- src/frob/tickets/_leases.py
- tests/gates_suite/test_tick_dead_worktree.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: new TICK015 rule id needs registration in _KNOWN_GATE_RULES and its docs
    table row
  actor: logan
  at: '2026-09-21'
- op: add
  glob: docs/modules/gates.md
  reason: new TICK015 rule id needs registration in _KNOWN_GATE_RULES and its docs
    table row
  actor: logan
  at: '2026-09-21'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
evidence:
- tests/gates_suite/test_tick_dead_worktree.py::TestTick015DeadWorktreeRequeue::test_deleted_worktree_fires_and_requeues
- tests/gates_suite/test_tick_dead_worktree.py::TestTick015DeadWorktreeRequeue::test_live_holder_is_untouched
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5121
branch: t-5121
---
Measured 2026-09-20 (scratchpad/STRANDED.md): 38 of 54 in-progress tickets were abandoned by dead agents while their worktree directories survived; orphaned_leases in src/frob/tickets/_leases.py returned 0 because liveness is tested by directory existence, not by process or branch activity. Fix: add the next free TICK0xx rule in src/frob/gates/_tickets_gate.py that, for every in-progress ticket, resolves the worktree and branch recorded on the ticket (depends on the start-transition ticket filed alongside this one) and errors when the path is absent, the branch is absent, or no live process holds it (reuse the process-presence verdict in src/frob/tickets/_worktree_sweep.py near line 351), then flips the ticket back to queued through the ledger commit path with a fail-log entry naming the dead worktree. Positive control: a fixture ticket started in a worktree whose directory is then deleted is reported by the rule and is queued again after frob check; a ticket with a live holder is untouched.