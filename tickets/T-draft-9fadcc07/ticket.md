---
id: T-draft-9fadcc07
title: Widen a11y_gate hook contract so _locate_statement_page gets a repo root
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
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
- src/frob/webapp/_a11y_statement.py
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
T-5454's done report documents _locate_statement_page(root, frameworks) as a deliberate known gap: a11y_gate's per-file hook contract (T-5323) has no reliable repo root to pass it, so it stays unwired into any production caller, kept only for direct tests. Widen the hook contract (or give per-file hooks a memoized repo-root handle) so this can wire in for real. Found while working T-5470 (its WIRE001 waiver named T-5454, now done, as the follow-up -- repointed here).