---
id: T-3349
title: sync docs/modules/tickets-verify-sweep.md for T-2521's measurement_note/completeness
  change
state: queued
kind: docs
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets-verify-sweep.md
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
T-2521 threaded a measurement_note string through revalidate_dispatchable_sweep_tickets/_maybe_drop_resolved_ticket's reason text and gained the shared _incomplete_tool_results completeness check via _matching_error_diagnostics. Was waived (frob:waive AFFECT001) at land time because docs/modules/tickets-verify-sweep.md was leased by T-2374 (now done, and its own scope included this doc file). Re-measured for T-3295: the doc's revalidate_dispatchable_sweep_tickets section still does not mention measurement_note or the completeness check. Add a short note describing both, mirroring the function's own current docstring.