---
id: T-3529
title: cross-file entity/architecture resolution for strata
state: queued
kind: feature
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
- docs/strata/entity_architecture.md
- design/frob.strata
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
docs/strata/entity_architecture.md's Scope of this first slice section documents a deliberate narrowing: 'of ENTITY' and 'binds MODULE' resolve only against entities/modules already parsed in the SAME file; cross-file entity references (an architecture in one file satisfying an entity declared in another) are not yet supported. T-3006 (the epic that built this first slice, now archived/done) never filed a specific follow-up for cross-file resolution. Found while binding NEGEXIST001's frob:until for T-3519. Build cross-file entity/architecture resolution, or if this narrowing is now considered permanent, reword the doc to drop the deferred-capability framing.