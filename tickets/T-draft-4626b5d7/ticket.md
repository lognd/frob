---
id: T-draft-4626b5d7
title: ticket new --points is not persisted
state: queued
kind: bug
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
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
`frob ticket new --points N` accepted the flag but the created ticket
carries `points: null` (measured 2026-09-24 filing the coord tree and the
tiers tree; every filer script had to follow with `frob ticket points`).
Fix: persist points at creation; positive control: new --points 3 then
show must print points 3.
