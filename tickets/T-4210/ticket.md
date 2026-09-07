---
id: T-4210
title: generated spec-table regen artifacts should use a shared lease or a land-time
  regen step, not an exclusive per-ticket scope item
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: low
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
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
Consumer F-321 (T-4135). An in-progress ticket's exclusive lease on a generated spec-table file blocked another ticket from committing its own regeneration, forcing a revert-and-refile. A file that is a mechanical artifact of any spec edit should not need an exclusive per-ticket scope item -- share the lease, or make regen a land-time step frob performs itself. Same family as F-292/F-309 per the report. Same source file as T-4172 (stale-lease reconciliation) -- sequence after it to avoid a scope collision, no hard dependency, different mechanism (this is about lease SHARING for generated files, T-4172 is about STALE lease detection). Fixture-testable: YES.