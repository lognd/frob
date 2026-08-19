---
id: T-2580
title: 'M5: MILE001/MILE002 milestone-deadlock gates'
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: high
blocked_by:
- T-2574
parent: T-2573
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_milestone.py
- src/frob/gates/__init__.py
- tests/test_gates_milestone.py
- docs/modules/tickets-data-storage.md
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_milestone.py
  reason: MILE001/MILE002 tests + doc anchor for milestone_gate closure
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: MILE001/MILE002 tests + doc anchor for milestone_gate closure
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: REG010 sync-gate-rules entries for MILE001/MILE002
  actor: logan
  at: '2026-08-19'
evidence:
- tests/test_gates_milestone.py::TestMile001::test_blocked_by_later_milestone_fires
- tests/test_gates_milestone.py::TestMile001::test_blocked_by_earlier_milestone_does_not_fire
- tests/test_gates_milestone.py::TestMile001::test_blocked_by_same_milestone_does_not_fire
- tests/test_gates_milestone.py::TestMile001::test_terminal_blocker_does_not_fire
- tests/test_gates_milestone.py::TestMile001::test_terminal_ticket_never_fires
- tests/test_gates_milestone.py::TestMile001::test_unresolved_milestone_does_not_fire
- tests/test_gates_milestone.py::TestMile002::test_descendant_in_later_milestone_fires
- tests/test_gates_milestone.py::TestMile002::test_descendant_in_earlier_or_same_milestone_does_not_fire
- tests/test_gates_milestone.py::TestMile002::test_terminal_descendant_does_not_fire
- tests/test_gates_milestone.py::TestMile002::test_terminal_ancestor_never_fires
- tests/test_gates_milestone.py::TestMile002::test_grandchild_descendant_fires
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: c4880b01768a51d074c3902e198de009343ee17e
---
Two gates, both ERROR:

- MILE001: a ticket `blocked_by` a ticket in a LATER milestone. This is
  a provable release deadlock -- the earlier milestone can never ship
  while it depends on work the later milestone hasn't done yet.
- MILE002: an epic/story whose descendant is in a LATER milestone. Same
  deadlock via the hierarchy, since `_done_transition_guard` already
  forbids closing an epic over an open descendant (verified: this guard
  already exists) -- MILE002 is that same rule projected onto
  milestones, catching it statically before close-time.

Both need positive controls in BOTH directions:
- a planted MILE001/MILE002 violation must FIRE.
- a legitimate same-milestone edge, or an edge where the blocker is in
  an EARLIER milestone, must NOT fire.

Register both in `_KNOWN_GATE_RULES` so `frob:waive MILE001`/
`frob:waive MILE002` bind correctly, and add them to that list's
`frob:enumerates` member set so DOCENUM001 stays clean -- find the
existing member set by name first (do not guess its location or
reinvent a second registry).

Depends on M1 (T-2574, field must exist) only. Does not depend on
M2/M3/M4/M4b -- these are static ledger-shape checks over `milestone`
and `blocked_by`/`parent`, independent of doable ordering or runs_last
semantics.