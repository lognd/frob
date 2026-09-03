---
id: T-3721
title: TEST006 remedy says make coverage but scaffold Makefile ships no coverage target
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
- src/frob/check/**
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
apollo FROBLEMS.md 2026-09-03: TEST006's remedy says 'run: make coverage' but the scaffolded Makefile intentionally ships no coverage target (its comment says frob coverage is the interface). The gate remedy text and the template disagree about the workflow entrypoint; fix the remedy string to say 'frob coverage' to match the scaffold's own documented entrypoint.

## Failure log
- 2026-09-03 attempt 1: Declared scope src/frob/check/** does not contain the defect: TEST006's remedy string ('run: make coverage', src/frob/gates/__init__.py line ~5147) lives in src/frob/gates/__init__.py, not under src/frob/check/**. Needs a ticket scoped to src/frob/gates/__init__.py instead.
