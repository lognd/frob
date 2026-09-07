---
id: T-4186
title: 'lint: a never/always/idempotent docstring or spec-row claim with no bound
  frob:invariant'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: T-4109
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docblocks.py
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
Consumer F-307/H3-4 (T-4109), consolidating identical findings independently reported as F-317/M-4, F-326/M2-5, F-327/M-2 (all T-4135), F-362/H4-6 (T-4166), F-386 item3 (T-4182). A cheap lint distinguishable from full frob:invariant coverage: an absolute-guarantee word (never/always/idempotent/fails closed/guaranteed) in a docstring, decision-record row, or spec-row clause with no invariant bound to it. Extend across Python and, per F-327/M-2, TypeScript. Fixture-testable: YES in Python today; TS variant not exercised here.