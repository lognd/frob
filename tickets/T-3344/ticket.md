---
id: T-3344
title: Clear gate:DRIFT findings (53 errors) for release gate
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- '**/*'
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
Sprint task: reduce unscoped frob check DRIFT errors from 53 to 0. Investigate histogram of rule ids/files first; fix real doc drift, frob ack verified-correct docs, never mass-ack.