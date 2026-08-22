---
id: T-2841
title: Fix I001 import-sort regression in T-2729's selfconform split (6 files)
state: queued
kind: bug
origin: human
created: '2026-08-21'
priority: medium
parent: T-2373
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_selfconform.py
- src/frob/strata/_selfconform_binding_rules.py
- src/frob/strata/_selfconform_core_rules.py
- src/frob/strata/_selfconform_kinds.py
- src/frob/strata/_selfconform_models.py
- src/frob/strata/_selfconform_surface_rules.py
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
T-2373 burned ruff I001 (import-sort) to zero and promoted it WARN->ERROR. T-2729's strata/_selfconform.py split (6 new modules) landed with unsorted import blocks, which the promoted-to-ERROR gate correctly caught as a regression the moment it appeared. Pure import reordering via ruff --select I001 --fix, zero behavior change. T-2729's agent has retired.