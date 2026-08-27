---
id: T-3057
title: Wire TDD001 ordering check into frob ticket land pre-land path
state: done
kind: feature
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
evidence_scope:
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ticket_land.py::TestCheckTddOrder::test_logs_a_warning_for_an_implementation_first_pair_without_blocking
- tests/test_ticket_land.py::TestCheckTddOrder::test_stays_quiet_when_no_tests_edges_are_touched
- tests/test_ticket_land.py::TestCheckTddOrder::test_never_refuses_the_land
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 75717e16e63c508da728f88cd22fec6b0632227c
---
## Description
T-3009 built `frob.gates._tdd_order.tdd_order_violations` (TDD001: a
`frob:tests` edge's artifact/implementation symbol must not be
introduced before its verifying test, checked via git ancestry
pre-land). It is deliberately NOT wired into `frob ticket land`'s
pre-land check path yet -- T-3009's scope was the check and its rule,
not the call-site wiring, mirroring how BUG002's own
`bug_repro_violations` is a separate call from `frob.tickets._land`.

## Plan
Wire `tdd_order_violations` into the pre-land check path
(`frob.tickets._land`), following `bug_repro_violations`'s own call-site
pattern: gather the ticket's touched `frob:tests` edges, run
`tdd_order_violations(worktree, edges)` against the worktree's own
unsquashed branch, and fail the land on any `Severity.ERROR` finding
(surface `Severity.UNRESOLVED` findings too, non-fatal, same posture as
every other UNRESOLVED-emitting gate).