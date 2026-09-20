---
id: T-5089
title: 'test_drain: stale _fake_probe after T-4556 added whole_land kwarg'
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/verify/test_drain.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN _probe_land_once's real signature (T-4556 added whole_land) WHEN test_drain's
    _fake_probe monkeypatches it THEN the fake accepts the same keywords and the test
    suite passes
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35448990233 (dev tip beedd71c4) failed all 3 platforms: TestRunDrainAsync::test_excludes_its_own_originating_land_pid. TypeError: _fake_probe() got an unexpected keyword argument whole_land. T-4556 (landed) added a whole_land bool param to _probe_land_once (src/frob/tickets/_leases.py) but this test file's local _fake_probe was never updated to accept it. Update the fake signature to match production.

## Failure log
- 2026-09-20 attempt 1: coordinator: in-progress with no worktree or branch carrying work; requeued for a fresh agent
