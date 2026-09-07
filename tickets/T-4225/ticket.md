---
id: T-4225
title: 'TODO001: bump severity for a frob:todo/skip guard whose reason names a production
  command or an unwired gate, not unwritten code'
state: queued
kind: feature
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
- src/frob/gates/_todo_fmt.py
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
Consolidates three independent arrivals: F-317/M-3 (T-4135 sub-epic shell round-3 -- a frob:todo correctly records an unwired gate as a gap, but TODO001 does not escalate a todo describing an unwired gate the way it might a plain code gap); F-362/M4-4 (T-4166 -- a describe.skipIf whose 20-line comment documents a coupling to npm run build resolves the coupling by disabling itself, with no frob:todo obligation attached); F-386 item 1 (T-4182 -- the identical skipIf-disables-itself shape recurring, explicitly citing round 4's own proposed fix). All three are one mechanism: a skip/todo guard naming a production command or an unwired gate is an obligation, not a resolution, and should require a tracked follow-up ticket the way a bare code TODO already does. Fixture-testable: YES, frob's own TODO001/skip-marker conventions.