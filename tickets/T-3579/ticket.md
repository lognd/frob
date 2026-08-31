---
id: T-3579
title: frob check crashes with FileNotFoundError on a stale closed-ticket scope glob
state: queued
kind: bug
origin: human
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets
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
Measured while landing T-3577: deleting a file that a CLOSED ticket's scope glob still names (tickets/T-3565/ticket.md: glob: tests/unit/test_conftest_sigbreak_faulthandler.py) makes EVERY frob check invocation in that worktree crash outright:

ERROR: main: unhandled exception during dispatch: [Errno 2] No such file or directory: '<worktree>/tests/unit/test_conftest_sigbreak_faulthandler.py'

Reproduced with --ticket-scoped, --only gates-fast, and other family combinations -- it is not specific to one --only family, so this is likely in a repo-wide evidence/coverage scan (COV003's own territory) that opens the glob-matched path directly instead of catching FileNotFoundError and reporting COV003 (missing evidence target) the way it is presumably meant to. Worked around in T-3577 by keeping the file present as a skip-stub rather than deleting it outright -- diagnose and fix the crash itself here so a future ticket does not need the same workaround.
