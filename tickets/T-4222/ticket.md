---
id: T-4222
title: 'strata: mark outbound fetch capabilities volatility=external; a volatility=external
  source may not ground a build-failing equality check'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4166
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
- src/frob/strata
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
Consolidates F-362/H4-2 (T-4166: a build node's grant to fetch third-party data carries no attribute saying that data is volatile, so nothing objects to comparing it for byte equality against a committed file) with F-386 item 7 (T-4182: the same gate restated, plus a note that a hand-picked field allowlist was implemented instead of a volatility classification, which is why the field partition is a judgement call rather than a structural fix). Not fixture-testable in frob's own tree: no external-fetch-grounding-a-build-oracle pattern exists here.