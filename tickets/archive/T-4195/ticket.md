---
id: T-4195
title: exempt files under tickets/T-xxxx/ created by ticket new from the filing ticket's
  own SCOPE001 check
state: dropped
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_refs.py
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
Consumer F-316 (T-4135). Every agent that files a follow-up ticket sees SCOPE001 fire on the new tickets/T-xxxx/ directory and must scope-add or explain it away. Files created by frob ticket new under tickets/ should be exempt from the filing ticket's own scope check. Fixture-testable: YES, consumer-blocking now (routine friction on every follow-up filing).

## Drop reason
- 2026-09-08: Premise re-verified against current main and does not hold: T-3298 (already landed, tests/gates_suite/test_prework.py::TestScopePrework::test_scope001_exempts_new_tickets_own_bookkeeping_shard_filed_from_another, currently passing) already exempts a newly-filed sibling ticket's tickets/<id>/ticket.md from the filing ticket's own SCOPE001 via the existing commit-attribution + T-1819 implicit tickets/<id>/** scope mechanism, for the normal case (frob ticket new auto-commits the new ticket file itself, GENERIC_COMMIT_UNMIRRORED). Also, the declared scope src/frob/gates/_refs.py was never where SCOPE001 lives -- the real implementation is src/frob/gates/__init__.py::scope_gate/_scope_gate_check_file/_commit_exempts_file plus frob.tickets._models.scope_matches. No live discovery to file: re-verification found the reported friction already closed, not a residual gap to defer.
