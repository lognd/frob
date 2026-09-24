---
id: T-5482
title: 'Windows-only: full suite INTERRUPTED after test_ticket_verbs_wait errors --
  failing set is a lower bound'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
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
Found while draining CI run 35951365410 (dev 9e0c89bb19), windows-latest job
only -- URGENT, affects CI signal integrity: the whole pytest run was
INTERRUPTED (SUITE-RESULT: DID-NOT-COMPLETE exitstatus=2 (INTERRUPTED)
collected=15507 (partial) failed=1 (partial, lower-bound)) immediately
after tests/unit/test_ticket_verbs_wait.py errored:
SUITE-RESULT-FAILED: tests/unit/test_ticket_verbs_wait.py (error)

This means the windows-latest job's failing-test list (35 node ids
reported) is a LOWER BOUND, not the true failing set -- whatever test(s)
would have run after this point never got the chance to report, and any
of them could also be failing. tests/unit/test_ticket_verbs_wait.py
itself needs investigating first (its own collection/run error, not a
normal assertion failure) since it appears to be what triggered the
interruption -- possibly a hang that tripped the runner's own timeout/
kill mechanism, given the file name ("wait").

Until this is fixed, windows-latest CI results should be treated as
incomplete/unreliable for anything after this test in collection order,
not just for the 35 named failures.
