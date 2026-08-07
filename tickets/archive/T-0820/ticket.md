---
id: T-0820
title: 'gates: wire a TICK-family frob check warning for undispatched-stale CRITICAL/HIGH
  tickets (T-0752 gate half)'
state: done
kind: feature
origin: human
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTick007UndispatchedStale::test_stale_critical_fires
- tests/test_gates.py::TestTick007UndispatchedStale::test_fresh_critical_is_silent
- tests/test_gates.py::TestTick007UndispatchedStale::test_medium_priority_never_fires
- tests/test_gates.py::TestTick007UndispatchedStale::test_blocked_ticket_is_silent
- tests/test_gates.py::TestTick007UndispatchedStale::test_real_repo_scan_runs_end_to_end_without_crashing
designated_repro_test: null
threat: null
component: null
---
T-0752 built the pure staleness-alarm computation (frob.tickets.undispatched_stale, dispatch_stale_hours, _dispatch_stale_thresholds -- src/frob/tickets/__init__.py) and wired it into frob ticket doable's row rendering (src/frob/app/ticket_runner.py), per its acceptance criterion's UNDISPATCHED row marker. The SAME criterion also asks for "AND frob check emits a TICK-family warning naming it" -- a new TICK-family gate (e.g. TICK007) that calls undispatched_stale over the doable set and emits a Violation per alarmed ticket, the same way TICK004 (queue rot) already does. That half requires touching src/frob/gates/__init__.py (and its TICK-family stage wiring), which is OUTSIDE T-0752's declared scope (src/frob/tickets/**, src/frob/app/ticket_runner.py, docs/modules/tickets.md). Filed as a separate ticket per the agent playbook's "found work outside scope -> file, don't fold in" rule. Reuse frob.tickets.undispatched_stale verbatim -- do not re-derive the staleness judgment in the gates module. Coordinate with T-0714 (doable diagnostics relocation to frob check) since both move doable-adjacent signal into the gate layer.