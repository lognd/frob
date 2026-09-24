---
id: T-draft-41d9b136
title: frob ci validity <run> and frob ci watch <run>
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.535.0
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
frob ci validity <run-id> and frob ci watch <run-id>: wrappers over frob.ci_validity (STILL VALID / STALE classification against the current diff) and a poll loop that emits the run's completion with per-job conclusions, at a rate that respects the API limit; coord watch calls this primitive. Positive control: a fixture whose touched symrefs classify as unrelated-to-diff is reported verbatim, not unknown.
