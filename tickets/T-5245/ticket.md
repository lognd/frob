---
id: T-5245
title: 'test_land_in_progress_window fixture drift: _refuse_if_land_in_progress_for_dispatch
  gained wait_timeout_s, test stub did not'
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/__init__.py
- tests/unit/test_land_in_progress_window.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
lease_force_releases:
- reason: promote before land (T-5166)
  staleness_reason: null
  actor: /home/logan/projects/frob
  at: '2026-09-21'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while burning down fresh CI run 35654510898, re-verified on current dev tip. tests/unit/test_land_in_progress_window.py::TestDispatchLayerWholeLandClassification::test_evidence_proceeds_while_only_land_lock_held and ::test_renumber_exits_while_only_land_lock_held both fail with TypeError: TestDispatchLayerWholeLandClassification._force_zero_wait.<locals>._zero_wait() got an unexpected keyword argument 'wait_timeout_s' at src/frob/app/ticket_runner/__init__.py:646. A recent change added a wait_timeout_s keyword argument to whatever _refuse_if_land_in_progress_for_dispatch calls at line 646, but this test file's own _force_zero_wait monkeypatch stub was not updated to accept it. Pure test-fixture drift (the production signature changed, the test double did not follow) -- fix by adding **kwargs or the explicit wait_timeout_s parameter to _force_zero_wait's inner _zero_wait.