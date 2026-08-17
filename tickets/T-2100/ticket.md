---
id: T-2100
title: 'TestRevalidateDispatchableSweepTickets: two tests intermittently interfere
  when run together (pre-existing)'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/unit/test_rapid_sweep.py
- src/frob/tickets/_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured (found while verifying T-2089)

Two tests in `tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets`
-- `test_fully_resolved_candidate_is_dropped` and
`test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition` --
each pass reliably in isolation but intermittently fail when run together
in the SAME pytest process (either order), even though each uses its own
unique `tmp_path`. Reproduced BEFORE T-2089's own fix landed (confirmed
at commit 0aeffe33a, T-2089's own ticket-start commit, via 5 repeated
runs of the same pair: 2 clean, 3 failed with different members failing
each time) -- this is pre-existing flakiness, not something T-2089's
cache change introduced.

Repro:

    for i in 1 2 3 4 5; do
      uv run pytest -o addopts="" tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_fully_resolved_candidate_is_dropped \
        tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition -q
    done

One observed failure: `test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition`
asserted `dispatched == ()` (an already-DROPPED ticket must never be
re-dropped) and got `('T-0001',)` instead -- the illegal
`dropped -> dropped` transition guard this test exists to lock in did
not hold, only when run immediately after the sibling test in the same
process. Since both tests use independent `tmp_path` fixtures, this
smells like in-process global/module-level state leaking across tests
(a cache keyed on something narrower than the full root path, or a
timing/mtime-based invalidation edge) rather than anything filesystem-
level -- not investigated further here, out of T-2089's own scope
(perf/caching only).

## Scope

Whichever module owns the leaking state -- likely `frob.tickets`'s v2
index cache (`_store.py`, seen logging "v2 index cache stale (mtime
changed)"/"hit" during the run) or `_is_transition_legal`'s own
resolution path -- plus `tests/unit/test_rapid_sweep.py` for a
regression test once the mechanism is understood.
