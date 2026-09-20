---
id: T-4950
title: Legacy indirect-call WIRE001 waivers are permanent by design (WIRE001 follow_up
  anchor)
state: queued
kind: docs
origin: human
created: '2026-09-19'
priority: medium
parent: T-4806
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/dup/_legacy_cs.py
- tests/unit/test_land_merge_conflict_drop.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: test_wire002_zero_against_live_repo passes with zero WIRE002 findings
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Anchor ticket (same shape as T-1820/T-1831) for the WIRE001 waivers on src/frob/dup/_legacy_cs.py::_collect_locals_cs, src/frob/dup/_legacy_cs.py::_serialize_cs_body (both: passed as a callable argument to _index_function in the same indirect-call shape as their pre-existing _cpp/_py siblings, which WIRE001 does not flag only because they are not new in a diff), and tests/unit/test_land_merge_conflict_drop.py::_seed_widget_worktree (test-only fixture helper, no production caller expected). These are permanently unflaggable-by-direct-call shapes, not TODOs to resolve -- this ticket stays queued as the follow_up anchor WIRE002 requires.