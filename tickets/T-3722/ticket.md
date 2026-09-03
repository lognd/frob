---
id: T-3722
title: frob test --all prints stale/wrong xdist addopts warning
state: queued
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/**
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
apollo FROBLEMS.md 2026-09-03: 'frob test --all' printed an ERROR claiming 'pytest addopts sets -n auto' on a repo whose addopts is just '-q', then reported PASS anyway. The message appears to fire from a stale template string or the wrong config source rather than the actual repo config.