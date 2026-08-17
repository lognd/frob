---
id: T-1778
title: Re-home a dangling WIRE001 follow_up citation off T-1743
state: queued
kind: docs
origin: human
created: '2026-08-07'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/unit/test_land_finish_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: true
anchor_reason: permanent WIRE001 waiver home for tests/unit/test_land_finish_guard.py:_add_worktree
  -- follow_up=T-1778 cites this ticket by design (re-pointed off the closing T-1743),
  so it must never reach a terminal state (T-1856)
land_commit: null
---
tests/unit/test_land_finish_guard.py:70's WIRE001 waiver cites follow_up=T-1743, which is closing -- re-point to this ticket instead so the waiver keeps a live tracker.

## Failure log
- 2026-08-08 attempt 1: This ticket's re-point work is already on main; it now anchors its own WIRE001 waiver (follow_up=T-1778) and must stay non-terminal forever per T-1856 -- recording as a fail attempt (not a real work failure) is the only existing mechanism land() has to publish a non-terminal ledger record; see T-1868 filed for the missing anchor skip-close path

## Done report

This ticket's stated work -- re-point tests/unit/test_land_finish_guard.py:70's
WIRE001 waiver off the closing T-1743 -- was already done on main by an
earlier commit (d285b6c5b43ed2deb7fe2e987f157e3d0564fc1d, "chore(tickets):
re-point T-1743's dangling WIRE001 follow_up citation"): the waiver's
follow_up already reads T-1778, verified directly against current main.

That leaves this ticket in the exact T-1856 anchor shape: the waiver now
cites T-1778 ITSELF as its live tracker, so T-1778 must never reach a
terminal state (WIRE002 disqualifies a done/dropped follow_up target,
same T-1490/T-1488 orphan-waiver class T-1856 exists to prevent). Marked
`anchor=True` via `set_anchor` (T-1856's library-level setter -- no CLI
yet, see T-1867) with a reason recording why, and requeued to `queued`
(no further active work) rather than closed/dropped.

Initially attempted a `drop` (the work looked finished at a glance) --
correctly refused by `_check_live_tracker_citations`/`LiveTrackerCited`
since T-1778 IS the citation's target. Un-did the drop (git reset in the
worktree, nothing had landed yet) rather than force through it.

Docs-kind ticket with no pytest surface of its own -- recording the
existing CLI-dispatch integration test as evidence per the T-0167
precedent (agent-playbook.md section 5).

### Changed
```
 tickets/T-1778/ticket.md | 6 ++++++
 1 file changed, 6 insertions(+)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
