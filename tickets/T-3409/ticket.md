---
id: T-3409
title: Update design/frob.strata SYS100 fs.read capability for stats/_agentic split
state: queued
kind: bug
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
T-3059 split src/frob/stats/_agentic.py's fs.read caller (_load_events) out into a new sibling module src/frob/stats/_agentic_shared.py. design/frob.strata's SYS100 fs.read capability list (line ~847) still names src/frob/stats/_agentic.py, which no longer performs any filesystem read directly -- it should be replaced with src/frob/stats/_agentic_shared.py. Could not fix directly under T-3059 because design/frob.strata was held by a live cross-worktree lease (T-3388) at the time; SELFAUDIT001 flags the drift (capability 'fs.read' observed at src/frob/stats/_agentic_shared.py:36 but not declared) until this lands.