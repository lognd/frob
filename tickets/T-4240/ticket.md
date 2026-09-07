---
id: T-4240
title: 'BASE001: a tracked ratchet/baseline file whose current violation count exceeds
  its baseline blocks land, reported by name'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: high
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_ratchet.py
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
Consumer F-326/H2-3 second half (the TESTRUN001 half is already covered by open ticket T-3988 -- attach evidence there, not here): frob check --ticket does not run the repo's own test suite, so nothing in the ticket loop observes a currently-red default branch; a red ratchet should block the next land rather than silently accumulating. Fixture-testable: YES, frob's own ratchet/baseline machinery.