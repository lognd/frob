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
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
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
Consumer F-307/H3-1 (T-4109): a rate-limit guard's test trips the lockout by calling the recorder directly, proving the guard reads a lockout without proving anything writes one. Reuses the WIRE001 call-graph resolver for a new invariant kind: every reader of state X has at least one in-tree caller of the writer, reachable from the same entry class as the reader. NOT the same mechanism as T-4151 (T-4151 is WIRE001 false negatives on existing callers; this is a positive effectiveness/closure check using the same resolver). Fixture-testable: the resolver mechanism YES with a synthetic read/write pair in frob's own tree; the rate-limit domain itself does not exist here. Consumer-blocking: latent for us.