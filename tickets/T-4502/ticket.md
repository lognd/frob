---
id: T-4502
title: 'Regression on dev CI: tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
  fails on all three legs after the T-4491..T-4414 lands'
state: queued
kind: bug
origin: agent
created: '2026-09-15'
priority: high
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN the dev branch at d6cfcaf99 WHEN tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
    runs THEN it passes on ubuntu, macOS and Windows
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
dev CI run 35046799264 (d6cfcaf99, first CI run on dev after landing T-4491 lease staleness, T-4492 work/sweep branch resolution + read_all_leases hoist, T-4496 dev-branch config, T-4414 batched post-land sweep): the Test step fails on all three legs with exactly one test, test_dry_run_reports_clean, AssertionError at tests/system/test_cli_ticket_land.py:120 ('ticket land: resolved root <tmp>/main'). The ticket-scoped lands did not run this system test (their touched-set selection missed it). Bisect among the four lands by running the test at each of their commits; the likely candidates are T-4492 (branch resolution in the land/dry-run path) and T-4414 (spawn_deferred_post_land_sweep now returns a -1 sentinel and touches .frob/rapid-sweep-window.json). Fix the code, not the test, unless the test pins a now-wrong expectation; add the offending file to scope with frob ticket scope.