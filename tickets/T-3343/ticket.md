---
id: T-3343
title: 'Fix gate errors: COV/TICK/REL/REG/REF clusters'
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
- tickets/**
- docs/**
- src/**
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
Sprint task: drive gate:COV(38) gate:TICK(9) gate:REL(5) gate:REG(3) gate:REF(3) self-gate errors to zero. Measure per-rule histogram first.