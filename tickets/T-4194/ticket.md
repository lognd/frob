---
id: T-4194
title: reword the stale land.lock reclaim message so it reads as resolved, not active
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: low
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
Consumer F-315 (T-4135). 'reclaiming orphaned land.lock -- prior holder pid ... confirmed NOT running' reads as an active lock and drove ten retries whose condition matched the word 'lock'. Reword to something like 'stale lock removed'; report the reclaim once, not on every invocation. Fixture-testable: YES, in frob's own land.lock code.