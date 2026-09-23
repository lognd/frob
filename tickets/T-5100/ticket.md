---
id: T-5100
title: 'test_ticket_runner_base_forward_t4105: stale spawn-fn fake after T-4550 added
  files= kwarg'
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.540.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_ticket_runner_base_forward_t4105.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.540.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
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

## Failure log
- 2026-09-20 attempt 1: coordinator: in-progress with no worktree or branch carrying work; requeued for a fresh agent
