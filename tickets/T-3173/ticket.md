---
id: T-3173
title: Ack the add_cmd_evidence anchor drift left by T-3156
state: queued
kind: docs
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_evidence.py
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
T-3156 legitimately changed src/frob/tickets/_evidence.py::add_cmd_evidence (wiring scope_has_python_surface into the record-time kind gate). The DRIFT001 anchor ack was never refreshed, so the finding raised quarantine on 2026-08-27 and killed T-3157's land via the backpressure-drain loop before the 590s wrapper timeout.

I dismissed it as coordinator to unblock deferred landing fleet-wide, with the reason recorded. The ack itself is still OWED -- this ticket exists so that obligation is enforced rather than living only as prose in a dismissal reason.

FIX: run 'uv run frob ack src/frob/tickets/_evidence.py::add_cmd_evidence' after confirming the 10 dependents are still accurate for the new body. Do not blanket-ack; verify the dependents first.