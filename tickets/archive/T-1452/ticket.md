---
id: T-1452
title: 'strata: design argument-level may scoping (may KIND of TARGET)'
state: dropped
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1440 parent: argument-level `may` scoping follow-up (design sketch item
5, explicitly deferred to documentation-only by T-1440's own acceptance
plan): e.g. `may "env.read" of "FROB_*"` narrowing WHICH env vars, fs
paths, or net hosts a grant covers, not just which FILES (`via`) may
exercise it. Natural follow-up once `via` itself has real migrated usage
(T-1440's sibling migration ticket) to learn argument-scoping shapes
from. Not designed in detail yet -- this ticket is a placeholder for that
design pass, not a ready-to-implement plan.

## Drop reason
- 2026-08-08: Duplicate of T-1478: both are T-1440's deferred argument-level may scoping follow-up (may KIND of TARGET). T-1478 is the real filed ticket surface/mutation-audit doc already points at via frob:until; T-1452 is an earlier docs-only placeholder predating that filing. Confirmed before implementing, per dispatch instructions. (absorbed by T-1478)
