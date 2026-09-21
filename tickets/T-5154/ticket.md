---
id: T-5154
title: persist mined done-transitions in .frob cache keyed by head sha for warm-cache
  frob ticket flow
state: queued
kind: feature
origin: human
created: '2026-09-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_flow.py
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
found while working T-5131: T-5131's batched fix (two tree-wide git spawns) satisfies the cold-run <10s acceptance criterion but not T-5131's warm-cache/one-new-commit <2s criterion, which needs mined transitions persisted (e.g. .frob/cache.db keyed by HEAD sha) and only the delta since the last mined sha re-walked. T-5131 itself only implements the batched-walk alternative its own Fix section offered, not the persistent-cache alternative.