---
id: T-3523
title: SYS106 never wires _cross_node_referenced_symbols/_node_real_public_surface
state: queued
kind: bug
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
- src/frob/strata/_selfconform.py
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
T-1870's own comment in src/frob/strata/_selfconform_surface_rules.py claims _node_real_public_surface and _cross_node_referenced_symbols (both still defined in that module after SYS104's removal) 'survive because SYS106 and SYS108 also depend on them'. Grep across the repo (2026-08-30) finds zero callers of either function anywhere -- src/frob/strata/_selfconform.py only mentions both names in docstrings/comments, never imports or calls them. SYS108 has its own working check (_duplicate_interface_violations) that does not use these two helpers. SYS106 appears to have never been built at all, or was removed without also removing this scaffolding and its now-false claim. Found while reviewing DEAD001 for T-3521. Either build SYS106 to actually consume these two helpers, or delete them (and correct/remove the stale comment) if SYS106 is not planned.