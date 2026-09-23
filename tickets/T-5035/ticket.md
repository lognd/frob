---
id: T-5035
title: Land-lock guard tests must hold the lock from a real foreign pid, not their
  own
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: T-4806
tier: ticket
sprint: null
runs_last: false
milestone: 0.533.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_reconcile.py
- tests/test_tickets_parent.py
- tests/test_tickets_priority.py
- tests/unit/verify/test_drain.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
evidence:
- tests/test_ticket_reconcile.py::TestReconcileApplyLandInProgressGuard::test_apply_refuses_and_writes_nothing_while_land_lock_held
- tests/test_tickets_parent.py::TestSetParentLandInProgressGuard::test_refuses_and_writes_nothing_while_land_lock_held
- tests/test_tickets_priority.py::TestSetPriorityLandInProgressGuard::test_refuses_and_writes_nothing_while_land_lock_held
- tests/unit/verify/test_drain.py::TestRunDrainAsync::test_excludes_its_own_originating_land_pid
designated_repro_test: null
acceptance:
- text: test_apply_refuses_and_writes_nothing_while_land_lock_held passes
  evidence:
  - tests/test_ticket_reconcile.py::TestReconcileApplyLandInProgressGuard::test_apply_refuses_and_writes_nothing_while_land_lock_held
- text: TestSetParentLandInProgressGuard test_refuses_and_writes_nothing_while_land_lock_held
    passes
  evidence:
  - tests/test_tickets_parent.py::TestSetParentLandInProgressGuard::test_refuses_and_writes_nothing_while_land_lock_held
- text: TestSetPriorityLandInProgressGuard test_refuses_and_writes_nothing_while_land_lock_held
    passes
  evidence:
  - tests/test_tickets_priority.py::TestSetPriorityLandInProgressGuard::test_refuses_and_writes_nothing_while_land_lock_held
- text: test_excludes_its_own_originating_land_pid passes
  evidence:
  - tests/unit/verify/test_drain.py::TestRunDrainAsync::test_excludes_its_own_originating_land_pid
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5035
branch: t-5035
---
CI run 35476139324 on dev: 4 tests fail because src/frob/tickets/_leases.py's land-lock probing now excludes the CALLING PROCESS's own pid as a foreign land holder (a real, intentional self-pid-exclusion feature, kept as-is per design decision). All 4 tests simulate a held land lock via fcntl.flock from within the SAME test process, writing os.getpid() into the lock file as the 'holder' pid -- so the self-exclusion now (correctly, by the new design) treats their synthetic lock as self-held and no longer refuses/excludes it, when the test's intent is to simulate a FOREIGN land holder. Fix: each of the 4 tests must hold the lock from a genuinely separate process -- spawn a sleeping subprocess with sys.executable (e.g. python -c 'import time; time.sleep(N)') and flock the lock file from within it, write ITS pid (not the test process's own) into the lock JSON, then run the guard/probe under test and assert it still refuses/excludes as a real foreign land. Test-only change, no src edits. NOTE: all 4 files are currently leased by other in-progress tickets (T-4627: test_tickets_priority.py, T-4623: test_tickets_parent.py + test_ticket_reconcile.py, T-4782: test_drain.py) -- this ticket cannot start until those leases clear; block on them.