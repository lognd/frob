---
id: T-4221
title: 'frob:invariant time-stable kind: discharge a wall-clock-dependent predicate
  by re-running its bound test with the clock advanced across a declared horizon'
state: queued
kind: feature
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
- src/frob/gates/_inv.py
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
Consumer F-362/H4-1 (T-4166): a check comparing a committed-artifact-derived value against wall-clock time passes today and fails tomorrow; every existing test supplies now and the artifact's timestamp from the same instant, so the whole class of 'passes today, fails tomorrow' is invisible. Add an invariant kind (e.g. frob:invariant time-stable horizon="180d") discharged by re-running the bound test with the clock advanced across the declared horizon; failing that, a narrower lint flagging a comparison between a committed-artifact value and new Date()/now() with no test that varies now. High value: ask what in frob's OWN tree is a function of wall-clock time and tested only at a single instant. Fixture-testable: YES, with a synthetic time-dependent function in frob's own tree.