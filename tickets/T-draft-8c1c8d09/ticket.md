---
id: T-draft-8c1c8d09
title: 'test_ticket_runner_base_forward_t4105: stale spawn-fn fake after T-4550 added
  files= kwarg'
state: in-progress
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
- tests/unit/test_ticket_runner_base_forward_t4105.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN _shared_check_spawn_fn's real signature (T-4550 added files, timeout)
    WHEN test_ticket_runner_base_forward_t4105's fake monkeypatches it THEN the fake
    accepts the same keywords and the test suite passes
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35448990233 (dev tip beedd71c4) failed all 3 platforms: TestDoneReportBaseResolution::test_default_main_resolves_to_no_base_forwarded and ::test_non_main_base_ref_is_forwarded. TypeError: _fake_shared_check_spawn_fn() got an unexpected keyword argument files. T-4550 (landed) added --files scoping support to _shared_check_spawn_fn (src/frob/app/ticket_runner/_verify.py) but this test file's local fake was never updated to accept the new kwarg. Update the fake signature to match production.