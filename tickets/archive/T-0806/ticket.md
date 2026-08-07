---
id: T-0806
title: 'tests: test_cli_check tmp fixtures broken on main -- git ls-files rc=128,
  3 system tests red'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tests/system/test_cli_check.py
- src/frob/app/check_runner.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/check_runner.py
  reason: 'Root-caused as two product bugs, not just fixture debt: (1) frob check

    --json leaked _refuse_ticket_lease_mismatch''s own gitio debug logging to

    stdout before the --json quiet clamp was ever entered

    (src/frob/app/check_runner.py::run), and (2) ProcessPoolExecutor(spawn)

    worker processes for CPU-bound gates never inherit the parent''s

    quiet_stdout_logs clamp, so they leaked their own default-DEBUG per-file

    parse logging onto the shared stdout fd (src/frob/gates/__init__.py). Both

    fixed inline; scope extended per T-0806''s own instructions ("fix

    (scope-add product files with a reason if product code is at fault)").

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'Root-caused as two product bugs, not just fixture debt: (1) frob check

    --json leaked _refuse_ticket_lease_mismatch''s own gitio debug logging to

    stdout before the --json quiet clamp was ever entered

    (src/frob/app/check_runner.py::run), and (2) ProcessPoolExecutor(spawn)

    worker processes for CPU-bound gates never inherit the parent''s

    quiet_stdout_logs clamp, so they leaked their own default-DEBUG per-file

    parse logging onto the shared stdout fd (src/frob/gates/__init__.py). Both

    fixed inline; scope extended per T-0806''s own instructions ("fix

    (scope-add product files with a reason if product code is at fault)").

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero
- tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta::test_delta_reports_only_new_violation
- tests/system/test_cli_check.py::TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage
- tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses
designated_repro_test: null
acceptance:
- text: GIVEN main WHEN tests/system/test_cli_check.py runs THEN TestCheckCleanProject::test_clean_code_exits_zero,
    TestCheckStampBaselineAndDelta::test_delta_reports_only_new_violation, and TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage
    pass; a run()-level exit-code test for the T-0787 lease-pin refusal is added once
    the fixture works
  evidence:
  - tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero
  - tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta::test_delta_reports_only_new_violation
  - tests/system/test_cli_check.py::TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage
  - tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses
threat: null
component: null
---
T-0787 reviewer verified these three nodes fail on CURRENT main with git ls-files exit 128 inside the tmp_path fixture (not-a-git-repository shape) plus JSON parse of polluted stdout -- pre-existing fixture debt unrelated to recent lands, no covering ticket found. Root-cause the fixture (missing git init? cwd leakage? the T-0768 quiet clamp changing expected stdout?), repair, and add the deferred end-to-end run() exit-1 test for ticket_lease_pin refusal (T-0787 reviewer action item b).