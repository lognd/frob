---
id: T-2589
title: Add TICK012 to gates.md's DOCENUM001 rule-catalog enumerates directive
state: dropped
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
found while working T-2561: TICK012 (frob.gates._tickets_gate._tick012_lease_scope_drift, T-2561) is a live, enforced gate rule (registered in _KNOWN_GATE_RULES and docs/design/registry/check-coverage.yaml's CHK-GATE-TICK012), but docs/modules/gates.md:13's frob:enumerates members="..." list for _KNOWN_GATE_RULES was NOT updated to include it -- DOCENUM001 fires. T-2561 could not fix this directly: docs/modules/gates.md was held by another in-progress ticket's live lease (T-2377) at the time, and widening T-2561's scope onto a path another ticket actively holds is a lease collision, not a legitimate scope expansion. Add TICK012 (and any other member CYCLE001 that also went stale in the interim) to the enumerated list once the lease is free.

## Failure log
- 2026-08-20 attempt 1: Premise already resolved: TICK012 is already present in both docs/modules/gates.md:13's frob:enumerates members= list and src/frob/gates/_waive.py's _KNOWN_GATE_RULES (added by a prior land after this ticket was filed). Measured: frob check --only docblocks --no-cache -> gate:DOCENUM reports 0 errors (TICK012 not among them; the only DOCENUM001 finding on gates.md is an unrelated QUEUE001 warning, outside this ticket's scope). Nothing to fix; requeuing rather than forcing scope.

## Drop reason
- 2026-08-21: already resolved: TICK012 is already present in docs/modules/gates.md frob:enumerates and in _KNOWN_GATE_RULES; measured frob check --only docblocks --no-cache reports gate:DOCENUM 0 errors (2026-08-21) (absorbed by T-2372)
