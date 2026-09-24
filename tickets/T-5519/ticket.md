---
id: T-5519
title: Wire TDD002 (xfail(strict=True) debt) into frob ticket land's pre-land check
  path
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-3068
parent: T-3004
tier: ticket
sprint: strata-vmodel
runs_last: false
milestone: v0.535.0
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
scope:
- src/frob/tickets/_land.py
- tests/test_tickets_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-3004
  reason: 'T-3004 decomposition: wiring follow-up to T-3068''s xfail(strict=True)
    debt marker'
  actor: logan
  at: '2026-09-24'
- field: sprint
  old_value: null
  new_value: strata-vmodel
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3068 shipped find_xfail_strict_tests/tdd_xfail_debt_violations
(src/frob/gates/_tdd_order.py, TDD002) as an unwired WARN gate function,
same "prove it in isolation" posture as T-3067's classify_ticket_commits.
Per owner directive (catalogued is not enforced is rejected) this needs
a wiring leaf: call tdd_xfail_debt_violations from
frob.tickets._land._check_tdd_order (the same pre-land call site TDD001
already uses) over the ticket's own diff-scoped touched .py files.

Positive control: a ticket branch whose latest commit still carries
@pytest.mark.xfail(strict=True) on a test fires TDD002 in the land
dry-run's gate output; the same branch with the marker removed by a
later commit stays quiet.
