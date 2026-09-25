---
id: T-draft-bf371f63
title: 'SYSDESIGN202: bursty-ingress/fixed-capacity design declaration with no interposed
  queue'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-dc6172d5
tier: ticket
sprint: sysdesign
runs_last: false
milestone: 0.539.0
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
- src/frob/sysdesign/_admission.py
- tests/fixtures/sysdesign/sysdesign202/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN203: bursty-ingress/fixed-capacity design declaration with no interposed queue
kind: feature
tier: leaf
parent: T-SYS-SD
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_admission.py, docs/modules/gates.md (SYSDESIGN203 row),
       tests/fixtures/sysdesign/sysdesign203/**
blocked_by: []
tag: Static: design

Research row 5.6: Azure Architecture Center, Queue-Based Load Leveling pattern,
https://learn.microsoft.com/en-us/azure/architecture/patterns/queue-based-load-leveling
(fetched, 208 lines). Lint condition: "Design model marks a workload as 'bursty ingress,
fixed-capacity consumer' with no queue declared between them flags."

Distinct from REL260/261 (queue.bounded_intake, existing): this rule is about the ABSENCE of a
queue at all between a declared-bursty producer and a declared-fixed-capacity consumer, not
about a queue's own intake bound once one exists -- REL260/261 has nothing to say if no queue
node is present in the graph at all.

Acceptance criteria: flags a strata design where a node with `attr bursty` (or equivalent
high-fanout/high-skew declaration) flows directly (no intervening `queue` node) into a node
with a fixed `capacity replicas N..N` (no autoscale range). Positive-control fixture:
tests/fixtures/sysdesign/sysdesign203/bursty-direct-to-fixed-capacity/**.
