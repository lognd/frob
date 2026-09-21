---
id: T-5212
title: Wire _rapid_caller_dependents to public_caller_dependent_files
state: queued
kind: feature
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
- src/frob/app/ticket_runner/_land_cmd.py
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
found while working T-4560: build_call_graph gained an opt-in include_public_callees flag and frob.graph.affects gained public_caller_dependent_files, but _land_cmd.py's _rapid_caller_dependents (out of T-4560's declared/implicit scope) still only calls the private-only caller_dependent_files. Wire it to also call public_caller_dependent_files (or replace the call) so the rapid land's --files dependents scope actually picks up callers of a changed PUBLIC symbol end to end.