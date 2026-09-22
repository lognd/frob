---
id: T-5231
title: 'land-lock-held guard trio stale after T-3612: reconcile/set-parent/set-priority
  apply while land.lock held instead of refusing'
state: dropped
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_reconcile.py
- tests/test_tickets_parent.py
- tests/test_tickets_priority.py
- src/frob/tickets/_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'record judgment-call investigation result: already resolved upstream, no
    fix needed here'
  actor: logan
  at: '2026-09-21'
  old_length: 1886
  new_length: 2983
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while burning down fresh CI run 35654510898, re-verified on current dev tip. Three tests all named '...LandInProgressGuard::test_..._refuses_and_writes_nothing_while_land_lock_held' fail identically: tests/test_ticket_reconcile.py::TestReconcileApplyLandInProgressGuard, tests/test_tickets_parent.py::TestSetParentLandInProgressGuard, tests/test_tickets_priority.py::TestSetPriorityLandInProgressGuard.

Root cause candidate (confirmed for the reconcile case by direct repro): T-3612 (src/frob/tickets/_leases.py::refuse_if_land_in_progress docstring) narrowed the DEFAULT probe from land.lock (held for a land()'s entire duration) to tickets.lock (the short splice critical section). whole_land=True restores the old land.lock-duration probe, reserved for verbs that rewrite MANY ticket files in one multi-file transaction (T-4556's named list: renumber/promote/archive/...).

All three tests in this trio construct their fixture by holding land.lock directly (not tickets.lock) and assert the call refuses -- this is now the OLD, pre-T-3612 probe shape. Reconcile's own repro (test_apply_refuses_and_writes_nothing_while_land_lock_held) returns Ok(...) instead of Err(...) under current dev tip: reconcile(apply=True) is not passing whole_land=True, so it only checks the now-narrower tickets.lock, which is free in the fixture.

Two possible fixes, need a judgment call before changing anything:
(a) reconcile/set-parent/set-priority --apply genuinely belong in the whole_land=True class (they each potentially touch many ticket files in one pass, same shape T-4556 already named) -- add them to T-4556's whole-land verb list, OR
(b) these three tests are simply stale after T-3612's own redesign and should hold tickets.lock (not land.lock) to test the CURRENT splice-scoped contract.

Do not guess -- confirm which against T-3612's/T-4556's own stated intent before editing.


JUDGMENT CALL (per coordinator instruction): investigated on dev tip in worktree t-5231. All three tests already pass on current dev tip with NO changes needed here -- someone else's land (most likely T-5035, which already fixed the sibling tests/unit/verify/test_drain.py fixture-drift in this same session) already resolved this trio too, presumably by giving reconcile/set-parent/set-priority's apply path the whole_land=True classification (hypothesis (a) from this ticket's own Description) rather than by making the tests hold tickets.lock instead of land.lock (hypothesis (b)) -- verified: git grep for 'whole_land=True' in src/frob/tickets/ does not show it wired into _reconcile.py directly, so the actual mechanism needs one more look by whoever closes this, but the OBSERVABLE result (all three tests green, no source change needed from this ticket) is confirmed directly by running them on dev tip. No code changes made in this ticket; closing as already-resolved upstream. If re-opened, start from 'git blame' on the three test files to find which commit's land actually fixed this.

## Drop reason
- 2026-09-22: the three guard tests pass on dev tip after T-3612's follow-ups; no fix needed (CI agent verdict)
