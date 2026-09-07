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
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata
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
Consolidates F-362/H4-2 (T-4166: a build node's grant to fetch third-party data carries no attribute saying that data is volatile, so nothing objects to comparing it for byte equality against a committed file) with F-386 item 7 (T-4182: the same gate restated, plus a note that a hand-picked field allowlist was implemented instead of a volatility classification, which is why the field partition is a judgement call rather than a structural fix). Not fixture-testable in frob's own tree: no external-fetch-grounding-a-build-oracle pattern exists here.