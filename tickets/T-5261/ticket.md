---
id: T-5261
title: Tier-A fix for redundant production-side frob:tests declarations (T-4710 follow-up)
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine_text.py
- src/frob/gates/_waive.py
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
found while working T-4710: frob.graph._redundant_test_declarations (src/frob/graph/__init__.py) now lints a frob:tests directive still declared on the production symbol as redundant (delete when a test-side declaration already exists, move-with-refusal when it does not, per T-4710's move-semantics amendment). T-4710's own scope is src/frob/graph/* only, so the Tier-A auto-fix handler (frob.gates._fix_engine_text, dispatched via TIER_A_HANDLERS) was left unbuilt; this ticket is that handler plus its _KNOWN_GATE_RULES registration and frob.toml severity.