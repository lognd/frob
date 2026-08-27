---
id: T-3178
title: Refresh add_cmd_evidence kind-gate description in tickets-data-storage.md
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
- docs/modules/tickets-data-storage.md
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
docs/modules/tickets-data-storage.md (~line 1416) still says 'add_cmd_evidence refuses with Err(EvidenceKindNotAllowed) for every kind except docs' -- stale since T-3156 widened the gate (any kind may use cmd evidence when scope_has_python_surface is False) and T-3045 added ux alongside docs. Found while acking DRIFT001 on add_cmd_evidence for T-3172; not a tracked frob:doc anchor on that symbol so it did not itself trip DRIFT001, but the prose is wrong and should be brought in line with docs/modules/tickets.md's already-updated description.