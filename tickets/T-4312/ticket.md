---
id: T-4312
title: Warn at ticket-close time when closing strands a live WIRE001 follow_up waiver
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/gates/_wire.py
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
T-4305 fixed one WIRE001 waiver stranded when its named follow_up ticket (T-4274) closed, turning a passing WIRE002 check into a CI-blocking failure with zero code changes. Nothing warns at close time: any ticket close can silently strand any frob:waive WIRE001 follow_up="T-####" naming it, discovered only later by a WIRE002 failure (or worse, on main/CI) that gives no hint the true cause was an unrelated ticket close. Add a check at 'frob ticket close'/'frob ticket land' time that scans live frob:waive WIRE001 directives for follow_up= references to the ticket being closed and warns (or blocks) so the closer can either add permanent="true" (if the waiver reasoning is structural, per T-1592's precedent) or repoint follow_up at a still-open ticket before the strand happens instead of after.