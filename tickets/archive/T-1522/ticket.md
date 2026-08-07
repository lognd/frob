---
id: T-1522
title: 'land: queue-drain commits must be durable across a same-invocation later unwind'
state: done
kind: bug
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_squash.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestLandPlanQueueDrainCommitsDurable::test_finalize_failure_after_merge_keeps_the_merge_commit
- tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits::test_no_foreign_commit_unwinds_to_the_merge_commit_not_pre_merge
- tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits::test_foreign_commit_after_own_last_commit_refuses_instead_of_discarding
- tests/test_ticket_land.py::TestLandPlan::test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge
- tests/test_ticket_land.py::TestLandPlan::test_dry_run_unwinds_the_merge
designated_repro_test: null
threat: null
component: null
---
T-1495 point 2 (filed as a follow-up, not implemented in T-1495 itself):
queue-drain commits (other tickets' lands absorbed into the same land
invocation as a primary ticket) must become durable the moment each one
is committed -- a later failure in the SAME invocation (e.g.
CrossTicketLeakage on the primary ticket) currently unwinds the whole
run, including unrelated already-drained lands (the T-1199/T-1200
queue-drain commits eaten by attempt-1/2 unwinds in the 2026-08-04
incident, tickets.md/T-1495's own Done report has the reflog detail).

This needs a real design decision beyond an unwind-boundary assertion:
either (a) each queue-drain commit needs to be pushed/durable
independently before the primary ticket's own steps run (so a later
primary-ticket failure only ever unwinds the primary ticket's own
commits, never the queue-drain ones already durable), or (b) the
queue-drain absorption mechanism itself needs to stop being a single
undo-able unit and instead commit-then-forget per drained ticket. T-1495
itself only fixes the concretely-identified unguarded reset path
(land_plan's own _land_plan_reset_hard) with a same-run unwind-boundary
assertion (_assert_reset_only_discards_own_commits) -- that assertion
protects against a FOREIGN process's interleaved commit being eaten, but
does not change the fact that within ONE run, queue-drained commits and
the primary ticket's own commits are currently treated as a single
all-or-nothing unwind unit.

Investigate the queue-drain absorption call path (search
`_absorbed_land_report`/stacked-sibling absorption, T-1001 churn item 2)
to find exactly where drained commits and the primary ticket's commits
share an unwind boundary, and design the split.