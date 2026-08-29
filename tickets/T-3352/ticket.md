---
id: T-3352
title: BUG002 repro check cannot capture order-dependent test-isolation leaks
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_verify.py
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
T-3341 hit a real defect (an env-var leak across pytest tests, order-dependent: the designated repro test PASSES in isolation both before and after the fix, and only fails when run in a specific multi-test sequence). BUG002's designated-repro check runs a single node id in isolation, so it cannot distinguish 'fixed' from 'never reproduces alone' for this whole class of bug (test pollution / leaked global state). Consider: allow a designated repro to be a pytest INVOCATION (multiple node ids, one process) rather than a single node id, so order-dependent regressions can be genuinely proven. T-3341 waived BUG002 with this ticket as follow_up since the underlying code fix is real and independently verified by hand (see T-3341's done report).