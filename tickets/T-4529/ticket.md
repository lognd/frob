---
id: T-4529
title: 'Regression on dev CI: tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
  fails on all three legs after the T-4491..T-4414 lands'
state: dropped
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
- src/frob/app/config.py
- tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py
- src/frob/__main__.py
- changelog.d/T-4515.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/config.py
  reason: 'root cause: AppConfig.from_args reads pyproject.toml relative to process
    CWD not the ticket verbs own --path/FROB_ROOT root, so ticket_land_branch leaks
    from whichever repo frob is invoked from into an unrelated --path target repo'
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/config.py
  reason: root cause fix location
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py
  reason: new unit test file covering the _pyproject_file_for_args fix
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/__main__.py
  reason: 'actual dispatch entrypoint: _dispatch_default hardcodes pyproject=Path(pyproject.toml)
    and never used AppConfig.from_args, so the from_args-level fix in config.py never
    runs for a real frob invocation; fix _dispatch_default to use the same root-aware
    resolution'
  actor: logan
  at: '2026-09-16'
- op: add
  glob: changelog.d/T-4515.md
  reason: hand-merge of dev left this land-written fragment out (the commit hook refuses
    adding fragments); the land's own merge restores it
  actor: logan
  at: '2026-09-16'
evidence:
- tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
designated_repro_test: tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
acceptance:
- text: GIVEN the dev branch at d6cfcaf99 WHEN tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
    runs THEN it passes on ubuntu, macOS and Windows
  evidence:
  - tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
dev CI run 35046799264 (d6cfcaf99, first CI run on dev after landing T-4491 lease staleness, T-4492 work/sweep branch resolution + read_all_leases hoist, T-4496 dev-branch config, T-4414 batched post-land sweep): the Test step fails on all three legs with exactly one test, test_dry_run_reports_clean, AssertionError at tests/system/test_cli_ticket_land.py:120 ('ticket land: resolved root <tmp>/main'). The ticket-scoped lands did not run this system test (their touched-set selection missed it). Bisect among the four lands by running the test at each of their commits; the likely candidates are T-4492 (branch resolution in the land/dry-run path) and T-4414 (spawn_deferred_post_land_sweep now returns a -1 sentinel and touches .frob/rapid-sweep-window.json). Fix the code, not the test, unless the test pins a now-wrong expectation; add the offending file to scope with frob ticket scope.

## Drop reason
- 2026-09-16: duplicate record: an earlier land promoted this draft to T-4502 on dev while the in-progress draft dir survived; the work lands as T-4502
