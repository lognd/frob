---
id: T-2578
title: 'M4: rescope runs_last to the ticket''s own milestone'
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: high
blocked_by:
- T-2574
- T-2576
- T-2577
parent: T-2573
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/tickets/_doable.py
- tests/test_tickets_milestone_runs_last.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_milestone_runs_last.py
  reason: new tests covering the M4 milestone rescope
  actor: logan
  at: '2026-08-19'
evidence:
- tests/test_tickets_milestone_runs_last.py::TestRunsLastMilestoneScoping::test_unmilestoned_runs_last_keeps_global_semantics
- tests/test_tickets_milestone_runs_last.py::TestRunsLastMilestoneScoping::test_unmilestoned_runs_last_becomes_doable_once_all_else_terminal
- tests/test_tickets_milestone_runs_last.py::TestRunsLastMilestoneScoping::test_milestoned_runs_last_blocked_by_same_milestone_open_work
- tests/test_tickets_milestone_runs_last.py::TestRunsLastMilestoneScoping::test_milestoned_runs_last_doable_once_same_milestone_work_terminal
- tests/test_tickets_milestone_runs_last.py::TestRunsLastMilestoneScoping::test_milestoned_runs_last_not_blocked_by_other_milestone_open_work
- tests/test_tickets_milestone_runs_last.py::TestRunsLastMilestoneScoping::test_runs_last_sibling_carve_out_preserved_within_a_milestone
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rescope `runs_last` (currently GLOBALLY scoped -- see epic body) to the
ticket's own milestone.

- A runs-last ticket becomes doable once every OTHER non-runs-last ticket
  IN ITS OWN MILESTONE is terminal, not once every other non-runs-last
  ticket in the entire ledger is terminal.
- Back-compat: a runs-last ticket with NO milestone set keeps today's
  exact global semantics (the current `_other_open_tickets` behavior,
  unchanged) -- do not force-migrate every runs_last ticket's semantics
  as a side effect of this change.
- Preserve the existing runs-last-sibling carve-out in
  `_other_open_tickets` (src/frob/tickets/_doable.py): fellow runs-last
  tickets are already excluded from the open-ticket count so two
  runs-last tickets never deadlock each other. Do not remove this --
  removing it is a mutual deadlock. (M4b handles the residual gap this
  carve-out leaves; do not attempt to close that gap here.)

Evidence must include T-1614 specifically: prove it becomes reachable
once its milestone's other work is terminal, and prove it does NOT
become reachable while that work is still open. Use a scratch/synthetic
fixture for the positive control, not a live mutation of T-1614 itself.

Depends on M1 (T-2574, field), M2 (T-2576, backfill -- T-1614 needs a
real milestone stamped to test against), and M3 (T-2577, sort key
change lands first so this ticket's own evidence measures against the
final _doable_candidates shape rather than a moving target).