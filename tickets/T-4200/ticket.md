---
id: T-4200
title: 'accept and other post-file verbs: fix duplicate-criterion-on-retry idempotency
  under harness backgrounding'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner
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
Consumer F-329 idempotency half (T-4135): a backgrounded accept call completed anyway; the retry added a duplicate criterion (#1==#2). accept (and siblings) should be idempotent on identical criterion text. The budget/backgrounding half of F-329 is the same class as T-4134 (frob ticket new lingering post-action work) -- attach as evidence there rather than refiling; this leaf covers only the idempotency defect. Fixture-testable: YES.