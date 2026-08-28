---
id: T-2710
title: Thread the real failing ledger path through GateError.QueueUnavailable (T-2684
  successor)
state: done
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_models.py
- src/frob/gates/__init__.py
- src/frob/check/_python.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_check.py::TestGatesErrorResultRealTicketError::test_real_ticket_error_names_specific_mode
- tests/unit/test_check.py::TestGatesErrorResultRealTicketError::test_dummy_sentinel_still_a_defensive_fallback
- tests/test_gates.py::TestRunGatesQueueFailureThreadsRealTicketError::test_duplicate_id_across_active_and_archive_surfaces_as_ticketerror
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2684 fixed QueueUnavailable's manufactured Diagnostic to carry a real
code=QUEUE001 and file=None (never the stale tickets.md path), but
GateError (a bare typani ErrorSet with no payload) still cannot carry
the ACTUAL failing ledger artifact (which tickets/T-####/ticket.md was
malformed, or which two paths collided on a duplicate id) up to
_gates_error_result -- the diagnostic names the failure MODE (queue
load failed) but not the specific failing PATH, which still requires a
separate `frob ticket list`/`frob ticket show <id>` run to find. Widen
GateError.QueueUnavailable (or add a sibling exception/result type
carrying the underlying TicketError + path) so _gates_error_result can
name the real failing artifact directly in the diagnostic message,
closing the remaining half of the "four failed land attempts, long
misdiagnosis" incident T-2684's own body describes.