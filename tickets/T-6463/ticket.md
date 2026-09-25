---
id: T-6463
title: STORE authority gaps and dropped rows
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-6430
tier: story
sprint: store-family
runs_last: false
milestone: 0.538.0
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
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 407
  new_length: 545
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Two halves: (1) close the 13 authority-citation gaps the research pass
left open, since the owner rule is every rule cites its authority and a
gap-flagged row is not yet dischargeable; (2) record every genuinely
dynamic-only (tier 4) research row as a dropped ticket with a reason,
never deleted -- these become `frob:tests`/EXPLAIN-style proof
obligations later, never a lexical-heuristic static rule now.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
