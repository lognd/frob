---
id: T-2778
title: WIRE001's call-graph walk cannot resolve a symbol wired only as a passed-by-name
  callback argument
state: queued
kind: bug
origin: agent
created: '2026-08-21'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
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
found while working T-2775: scripts/wait_for_land_slot.py::_print_tick is a real, live production callback -- main passes it by name as wait_for_slot's on_tick argument on every --verbose invocation, exercised directly by TestWaitForLandSlotMain::test_verbose_adds_per_tick_lines_to_stderr -- but WIRE001 still flags it as having no caller outside its own tests. The detector's call-graph walk apparently only resolves direct Call-expression sites, not a bare Name reference passed as a callback/keyword-argument value. This is a real, non-test-tree instance of the same shape T-1592's _wire002_is_permanent_test_helper_waiver already special-cases for tests/ private helpers, but that escape hatch is deliberately restricted to the test tree (T-1592's own docstring: 'restricted to the test tree so production code cannot use this to dodge real wiring'), so scripts/wait_for_land_slot.py::_print_tick currently carries a frob:waive WIRE001 with a follow_up pointing at this ticket instead. Fix: either extend WIRE001's own call-graph resolution to recognize a symbol passed by name as a callback argument as wired, or provide a narrower, non-test-tree-restricted escape hatch for this exact shape (a private top-level function passed by name to a same-module caller as a callback) with the same anti-abuse care T-1592 applied.