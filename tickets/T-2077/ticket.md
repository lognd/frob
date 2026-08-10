---
id: T-2077
title: 'ARCH001: split _file_regression_ticket and run_deferred_post_land_sweep in
  _rapid_sweep.py'
state: done
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: new tests added for the ARCH001 split's extracted helpers
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_rapid_sweep.py::TestRegressionCountLine::test_true_count_known
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before
- tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_new_findings_file_a_ticket_and_rebaseline
designated_repro_test: null
acceptance:
- text: ARCH001 absent for src/frob/app/ticket_runner/_rapid_sweep.py in frob check
    --only archgate
  evidence:
  - tests/unit/test_rapid_sweep.py::TestRegressionCountLine::test_true_count_known
  - tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before
  - tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_new_findings_file_a_ticket_and_rebaseline
threat: null
component: null
anchor: false
anchor_reason: null
---
Two functions exceed ARCH001's 60-line threshold: _file_regression_ticket (174 lines, line 1000) and run_deferred_post_land_sweep (125 lines, line 1742). Split into smaller helpers without behavior change. No-behavior-change refactor.