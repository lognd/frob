---
id: T-4188
title: 'frob:invariant call-graph-closure kind: a symbol reading a guard state must
  have a reachable in-tree writer'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4109
tier: ticket
sprint: null
runs_last: false
milestone: 1.1.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.538.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.538.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer F-307/H3-1 (T-4109): a rate-limit guard's test trips the lockout by calling the recorder directly, proving the guard reads a lockout without proving anything writes one. Reuses the WIRE001 call-graph resolver for a new invariant kind: every reader of state X has at least one in-tree caller of the writer, reachable from the same entry class as the reader. NOT the same mechanism as T-4151 (T-4151 is WIRE001 false negatives on existing callers; this is a positive effectiveness/closure check using the same resolver). Fixture-testable: the resolver mechanism YES with a synthetic read/write pair in frob's own tree; the rate-limit domain itself does not exist here. Consumer-blocking: latent for us.