---
id: T-4992
title: Fix stale test fixture stub missing files kwarg (ticket_runner base_forward
  T-4105 tests)
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
blocked_by:
- T-5100
parent: T-4806
tier: ticket
sprint: null
runs_last: false
milestone: 0.541.0
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
  new_value: v0.541.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: test_default_main_resolves_to_no_base_forwarded passes
  evidence: []
- text: test_non_main_base_ref_is_forwarded passes
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35476139324 on dev: both tests in tests/unit/test_ticket_runner_base_forward_t4105.py TestDoneReportBaseResolution fail with TypeError: _fake_shared_check_spawn_fn() got an unexpected keyword argument 'files'. src/frob/app/ticket_runner/_verify.py now calls _shared_check_spawn_fn with a files kwarg that the test's fake stub predates. Add a files parameter to the fake so it matches the real callable's current signature.