---
id: T-3259
title: Add TICK014 to docs/modules/gates.md's rule-catalog enumeration
state: dropped
kind: docs
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: 0.534.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.533.0
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-16'
- field: milestone
  old_value: v0.533.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-16'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3092 added TICK014 (frob.gates._empty_diff_close.empty_code_diff_violations, registered in _KNOWN_GATE_RULES) but could NOT add it to docs/modules/gates.md's #rule-catalog frob:enumerates list -- that file is leased by in-progress T-2988 (Docstrings rework), and T-3092's own scope explicitly avoided it, wiring TICK014's frob:doc anchor into docs/modules/tickets-data-storage.md instead (a valid but secondary anchor). DOCENUM001 currently fires: 'frob:enumerates at docs/modules/gates.md#rule-catalog claims a stale member list ... (doc omits: TICK014)'. Once T-2988 releases its lease, add TICK014 to the #rule-catalog enumeration in docs/modules/gates.md (one line, matching MILE003/MILE004's own entries) to clear DOCENUM001.

## Drop reason
- 2026-09-19: already resolved on dev: TICK014 is present in docs/modules/gates.md's enumerates members list and rule table (line 60); the 2026-09-17 lease only blocked sibling lands
