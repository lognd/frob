---
id: T-3154
title: 'post-land sweep regression from T-3145: 1 new (rule, file) identit(ies) (SEC110)'
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
- tests/test_worktree_lease_env_ambient.py
findings:
- - SEC110
  - tests/test_worktree_lease_env_ambient.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): SEC110 fix is a lint waiver comment addition
    only (frob:waive on an existing os.environ write) -- no runtime behavior changed,
    same fixture logic before and after; nothing for BUG002 to reproduce'
  actor: logan
  at: '2026-08-27'
  old_length: 1423
  new_length: 1653
evidence:
- tests/test_worktree_lease_env_ambient.py::TestAmbientFrobWorktreeDoesNotLeakIntoTests::test_new_ticket_against_unrelated_repo_is_unaffected_by_an_ambient_frob_worktree
- tests/test_worktree_lease_env_ambient.py::TestAmbientFrobWorktreeDoesNotLeakIntoTests::test_opt_in_worktree_lease_guard_still_fires_when_deliberately_set
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-3145 at commit 3886bd21206dddd3e8f59e259814b06959afa1f9 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- SEC110  tests/test_worktree_lease_env_ambient.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- SEC110  tests/test_worktree_lease_env_ambient.py  -> attributed to T-3145 (commit 3886bd21206d, already closed/dropped -- filed below) via tests/test_worktree_lease_env_ambient.py::TestAmbientFrobWorktreeDoesNotLeakIntoTests

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:no-behavior-change reason="SEC110 fix is a lint waiver comment addition only (frob:waive on an existing os.environ write) -- no runtime behavior changed, same fixture logic before and after; nothing for BUG002 to reproduce"