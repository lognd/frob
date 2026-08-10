---
id: T-1912
title: 'post-land sweep regression from T-1893: 2 new error(s) (SUPPRESS001)'
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/frob-suggest.py
- .claude/hooks/frob-timeout-guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_suppress_hooks_t1912.py
  reason: 'Neither hook file has a pytest surface of its own; the ticket needs a real

    fail-then-pass regression test (bug kind, so --evidence-cmd is not

    available) proving SUPPRESS001 catches a stale ty-ignore suppression and

    stays clean once removed. Adding one new test file to scope.

    '
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: tests/unit/test_suppress_hooks_t1912.py
  reason: using existing tests/test_gates_suppress.py::TestSuppress001RepoWideLock.test_repo_is_currently_clean
    as evidence instead of a new test file
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_gates_suppress.py::TestSuppress001RepoWideLock::test_repo_is_currently_clean
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1893 at commit 1a795d6af39a801fa32acec4067c2b8c222f3858 found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- SUPPRESS001  .claude/hooks/frob-suggest.py
- SUPPRESS001  .claude/hooks/frob-timeout-guard.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- SUPPRESS001  .claude/hooks/frob-suggest.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SUPPRESS001  .claude/hooks/frob-timeout-guard.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.