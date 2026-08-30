---
id: T-3475
title: triage two new EXHAUST002 findings unrelated to the isdigit-guard class
state: in-progress
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
- src/frob/tickets/_new_renumber.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-2568 (may-raise resolver isdigit-guard discharge). Two EXHAUST002 findings appeared in the corpus since T-2568 was filed that are NOT guard-predicate cases at all -- a different bug class, out of T-2568's scope: scripts/fleet_status.py::_true_flock_holder_pid (T-3093) leaks StopIteration uncaught; src/frob/tickets/_new_renumber.py::_open_and_lock_counter_file (T-3026/T-2952) leaks TicketLockUnavailable uncaught. Triage each: catch/declare/frob:raises as appropriate, or waive with a specific reason if intentional propagation.