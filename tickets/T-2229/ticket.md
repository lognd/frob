---
id: T-2229
title: 'TICK004/fleet_status rot report tells an operator to ''work it'' on an already-decomposed
  epic (T-1623: children T-2223/T-2224 in-progress, epic still reported rotting with
  no acknowledgment)'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- src/frob/gates/_tickets_gate.py
- tests/test_tickets_priority.py
- tests/unit/test_coordinator_scripts.py
evidence_scope:
- tests/test_tickets_priority.py
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_priority.py
  reason: new repro/regression tests for the decomposed-epic rot fix
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: new repro/regression tests for the decomposed-epic rot fix
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_tickets_priority.py::TestTick004QueueRot::test_decomposed_epic_gets_a_distinct_message_not_work_it
- tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_decomposed_epic_prints_under_its_own_heading_not_needs_decomposition
designated_repro_test: tests/test_tickets_priority.py::TestTick004QueueRot::test_decomposed_epic_gets_a_distinct_message_not_work_it
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TICK004 (`_tick004_queue_rot`, `src/frob/gates/_tickets_gate.py`) and
`scripts/fleet_status.py`'s TICKET ROT section both flag a queued/planned
epic/story past its rot threshold with the generic "work it" message, even
when it has already been decomposed -- children exist on main with
`parent: <this id>` and are actively being worked. Measured live: T-1623
(critical, 11d, threshold 3d) is reported rotting, but T-2223 and T-2224
both carry `parent: T-1623` on main and are in-progress. The recommended
action ("work it") has already effectively been taken; the epic itself is
correctly still `queued` (moving it to `in-progress` would hold file
leases it never uses -- the T-1686 root-lease-leak shape) but the ROT
alarm on it is now noise, the same defect SHAPE T-2200 fixed for
runs_last tickets (recommending an action that cannot/need not be taken).

## Do NOT fix it this way

- Do NOT infer decomposition from ticket TITLE text or a hand-authored
  allowlist of epic ids -- read `parent` as a STRUCTURED field off the
  CHILD ticket records in the queue (`Ticket.parent`), not by string-
  matching.
- Do NOT silence rot for every epic/story tier -- an epic/story with NO
  children at all must STILL rot (must-still-pass control). Only an
  epic/story that has at least one non-terminal (not done/dropped) child
  ticket referencing it via `parent` should have its rot message change;
  and only silencing epics whose EVERY child is terminal (done/dropped)
  while the epic itself is still queued is a further, separate question
  -- start narrow: distinguish "genuinely undecomposed" (still rotting,
  unchanged message) from "decomposed and being worked" (distinct
  message, still reported, never dropped from the report).
- Do NOT move a decomposed epic to `in-progress` to silence the alarm --
  a `tier=epic` ticket left `in-progress` holds file leases it never
  uses, and a lease recorded against the shared root is permanently
  unreclaimable (T-1686's own incident).

## Scope note

Same two files as T-2200 (`scripts/fleet_status.py`,
`src/frob/gates/_tickets_gate.py`) but a DISTINCT rule (parent/child
decomposition state, not a `runs_last` flag) -- filed separately per the
coordinator's own T-2200-series triage rather than widening T-2200's
scope mid-series.