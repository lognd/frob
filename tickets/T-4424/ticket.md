---
id: T-4424
title: TICK004 rot severity should respect sprint/milestone triage
state: done
kind: feature
origin: human
created: '2026-09-11'
priority: critical
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
- tests/*tick004*
- tests/*tickets_gate*
- tests/test_tickets_priority.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_priority.py
  reason: the actual TICK004 test file wasn't matched by the original scope globs
  actor: logan
  at: '2026-09-11'
body_changes:
- mode: set
  reason: full ticket body with 14 example ids and required behavior, from CI self-gate
    triage
  actor: logan
  at: '2026-09-11'
  old_length: 0
  new_length: 3049
evidence:
- tests/test_tickets_priority.py::TestTick004QueueRot::test_sprinted_ticket_past_2x_threshold_since_created_is_quiet
- tests/test_tickets_priority.py::TestTick004QueueRot::test_unsprinted_ticket_past_2x_threshold_still_errors
- tests/test_tickets_priority.py::TestTick004QueueRot::test_sprinted_ticket_with_no_recorded_assignment_date_fails_safe_quiet
- tests/test_tickets_priority.py::TestTick004QueueRot::test_epic_with_in_progress_child_stays_quiet_regardless_of_sprint
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI self-gate run 34556421981 (ubuntu leg, log run8-103129946930.log) reports
gate:TICK 12 error-severity findings, all TICK004. `_tick004_queue_rot`
(src/frob/gates/_tickets_gate.py) escalates a queue-rot finding from WARN to
ERROR whenever `age_days > threshold * 2`, computed purely from `t.created`
against the priority's rot-day threshold -- it never reads `sprint` or
`milestone`, so a ticket that has already been triaged into a sprint still
rots and still escalates to ERROR exactly like an untriaged one.

OWNER CONTEXT (2026-09-11): the backlog is being organized into scrum
sprints, each sprint a minor version toward v1.0.0. A ticket assigned to a
sprint (or milestone) IS triaged by definition -- it should not report as
queue rot at all, or should have its rot clock restart at the
sprint-assignment date rather than at `created`.

THE 12 ERROR-SEVERITY EXAMPLES (all high-priority, threshold 7d, escalation
at >14d, all measured at 16d since `created`, none carry a sprint):
T-2982, T-3004, T-3008, T-3010, T-3032, T-3047, T-3048, T-3049, T-3053,
T-3067, T-3068, T-2994.

TWO EPIC-BY-CHILDREN EXAMPLES (already correctly suppressed to WARN by the
existing T-3399 decomposed-epic cap, cited here so the fix does not
regress them): T-0969 (46d, epic, has an active non-terminal child) and
T-1273 (44d, same shape). These illustrate the "epics/stories with open
children are measured by their children, not themselves" requirement below
-- they must stay quiet exactly as they do today.

REQUIRED BEHAVIOR
1. A queued/planned ticket with `sprint` (or `milestone`) set is NOT rot.
   Its rot clock restarts at the ticket's SPRINT-ASSIGNMENT DATE, not
   `created` -- read from the ledger's own transition record
   (`kind_history`/`body_changes`/whatever field actually carries the date
   the sprint was set; do NOT use file mtime). If no such record exists for
   when `sprint` was set, fail safe to "not rotting" rather than guessing.
2. Unsprinted high-priority tickets past 2x threshold keep escalating to
   ERROR exactly as today -- this fix narrows false-positive rot on triaged
   work, it does not weaken the untriaged case.
3. Epics/stories with open (non-terminal) children continue to be measured
   by their children's progress, not their own age (existing
   `_epic_children_all_stalled`/`is_decomposed` machinery) -- a sprint-
   assigned epic sitting queued while children move must stay quiet, same
   as an epic with no sprint but active children does today.

TESTS REQUIRED
- Sprinted ticket past 2x threshold since `created` (but recently
  sprint-assigned) -> no finding.
- Unsprinted ticket past 2x threshold -> ERROR, unchanged from current
  behavior.
- Epic with an in-progress (or otherwise active, per existing
  `is_decomposed`/`_epic_children_all_stalled` logic) child -> quiet,
  regardless of sprint.

SCOPE: src/frob/gates/_tickets_gate.py (the TICK004 rule) plus its test
file(s). Do not touch ticket priorities or states -- a planner agent is
concurrently setting sprint/parent fields across the ledger.