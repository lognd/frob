---
id: T-4224
title: 'gate: after a bound test run, tracked-file git status must be unchanged, or
  the test that wrote is named as a finding'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: T-4166
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates
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
Consumer F-362/M4-7 (T-4166): no gate asserts that running the test suite is side-effect-free on the working tree; a suite that writes to tracked files makes every clean-tree measurement conditional on whether the suite ran (it also silently rewrote a licenses document in the consumer's repo). Cheap and exact: snapshot git status --porcelain before and after a bound test run; any newly-modified tracked file is a finding naming the test. Fixture-testable: YES, directly against frob's own test suite right now -- this is worth running once as a self-check independent of shipping the gate.