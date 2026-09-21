---
id: T-5202
title: register PERF015-018 in frob.toml, docs/modules/gates.md and _KNOWN_GATE_RULES
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
- frob.toml
- docs/modules/gates.md
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
found while working T-5136: PERF015-018 (frob.perf._loop_variant, frob.perf._cache_effects) are implemented and wired into perf_rules, but frob.toml (severities table) and docs/modules/gates.md (rule docs) both carried live cross-worktree leases (T-5138, T-5121) when T-5136 started and were removed from its scope; _KNOWN_GATE_RULES (src/frob/gates/_waive.py) was never in T-5136's declared scope at all. Add PERF015=warn .. PERF018=warn (or the repo's chosen tier) to frob.toml, a docs/modules/gates.md row per rule, and the four rule ids to _KNOWN_GATE_RULES so frob:waive PERF015..PERF018 is recognized.