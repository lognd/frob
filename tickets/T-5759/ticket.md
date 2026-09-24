---
id: T-5759
title: Wire INVLVL001 into frob check's gate dispatch (blocked by T-3010 lease)
state: dropped
kind: feature
origin: human
created: '2026-09-24'
priority: high
parent: T-3008
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/gates/__init__.py
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
found while working T-3008: invariant_level_gate (src/frob/gates/_invariant_level.py) is written and tested but not registered in _ALL_GATES/_GATE_STAGE_GROUPS/_build_thread_jobs (src/frob/gates/__init__.py) or _KNOWN_GATE_RULES (src/frob/gates/_waive.py) because both files were held by T-3010's live scope lease at the time. Once T-3010 lands (or its lease frees), register invariant_level_gate the same way MSCLOSE001/VMOD001 are registered.

## Drop reason
- 2026-09-24: folded into T-3008 once T-3010's lease on gates/__init__.py and _waive.py released -- INVLVL001 registered directly in T-3008's own land (absorbed by T-3008)
