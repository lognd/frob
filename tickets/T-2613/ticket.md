---
id: T-2613
title: Sync docs/modules/gates.md frob:enumerates member list (DOCENUM001, includes
  MILE003)
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- docs/modules/gates.md
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
DOCENUM001 already fires red on main (pre-existing, confirmed before T-2576 touched anything): docs/modules/gates.md's frob:enumerates anchor for _KNOWN_GATE_RULES omits CYCLE001 and TICK012. T-2576 (MILE003 registration) adds MILE003 to _KNOWN_GATE_RULES, which needs the same doc sync, but docs/modules/gates.md is leased by T-2377 (Burn EXHAUST002/EXHAUST003 to zero) so T-2576 could not add it to its own scope. Once T-2377 releases the lease (or coordinate a shared land), run frob fix (fix_docenum001_enumerates_sync) or hand-edit the members= list to include CYCLE001, MILE003, TICK012 (and re-verify no further names have drifted in the meantime).