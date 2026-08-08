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
---
tests/unit/test_land_finish_guard.py:70's WIRE001 waiver cites follow_up=T-1743, which is closing -- re-point to this ticket instead so the waiver keeps a live tracker.

## Failure log
- 2026-08-08 attempt 1: This ticket's re-point work is already on main; it now anchors its own WIRE001 waiver (follow_up=T-1778) and must stay non-terminal forever per T-1856 -- recording as a fail attempt (not a real work failure) is the only existing mechanism land() has to publish a non-terminal ledger record; see T-1868 filed for the missing anchor skip-close path