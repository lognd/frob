---
id: T-1180
title: 'coverage pipeline: flake-tolerant end-to-end -- serial rerun of failures,
  stale-data cleanup, deflation guard before stamp'
state: done
kind: bug
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- src/frob/testing/**
- src/frob/gates/**
- tests/test_coverage.py
- tests/test_gates.py
- design/frob.strata
- docs/modules/gates.md
- frob-coverage.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: 'T-1180: TEST011-floor unit coverage lives in tests/test_gates.py next to
    the rest of stamp_coverage/TestCoverageLoad tests; new top-level test class needs
    the SYS104 design/frob.strata interface= declaration to keep self-model clean'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: 'T-1180: TEST011-floor unit coverage lives in tests/test_gates.py next to
    the rest of stamp_coverage/TestCoverageLoad tests; new top-level test class needs
    the SYS104 design/frob.strata interface= declaration to keep self-model clean'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-1180: AFFECT001 requires touching the docs/modules/gates.md public-api/error-types
    sections stamp_coverage/GateError changes affect'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: frob-coverage.lock.json
  reason: 'T-1180: the in-dispatch make coverage validation run refreshed the committed
    coverage lock via stamp_coverage, the exact artifact this ticket modifies the
    write path of'
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_refuses_below_deflation_floor
- tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_deflation_floor_skipped_below_min_known_modules
- tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_first_pass_failure_does_not_abort_the_recipe
- tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_rerun_is_serial_and_scoped_to_last_failed
- tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_combine_xml_stamp_run_unconditionally_after_the_rerun
- tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_target_exit_reflects_final_status_not_always_zero
designated_repro_test: null
acceptance:
- text: GIVEN make coverage WHEN the parallel suite has failures THEN the failed tests
    are re-run once serially without coverage-halting, and only still-failing tests
    fail the target -- load-sensitive flakes (the four known self-model/serve-watch
    specimens) no longer block combine/xml/stamp
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_refuses_below_deflation_floor
  - tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_deflation_floor_skipped_below_min_known_modules
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_first_pass_failure_does_not_abort_the_recipe
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_rerun_is_serial_and_scoped_to_last_failed
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_combine_xml_stamp_run_unconditionally_after_the_rerun
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_target_exit_reflects_final_status_not_always_zero
- text: GIVEN combine runs THEN stale .coverage* files from prior aborted runs are
    removed first and the combine reports consuming every fresh worker file; a coverage.xml
    whose module-coverage fraction is below a sanity floor refuses to stamp (extending
    TEST011's deflation heuristic into a hard pre-stamp guard)
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_refuses_below_deflation_floor
  - tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_deflation_floor_skipped_below_min_known_modules
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_first_pass_failure_does_not_abort_the_recipe
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_rerun_is_serial_and_scoped_to_last_failed
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_combine_xml_stamp_run_unconditionally_after_the_rerun
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_target_exit_reflects_final_status_not_always_zero
threat: null
component: null
---
Three consecutive coverage runs failed to produce a trustworthy coverage.xml on 2026-07-28/29: (1) corrupted coverage shim broke combine silently; (2+3) four load-sensitive tests (three strata self-model + serve-watch tick, all pass in isolation, verified twice) fail only under xdist+coverage parallelism and halt the recipe before combine; a manual combine then consumed 2 of 7 data files (stale-file skip). The TEST005 bucket (~600 warnings) cannot be honestly recounted until this pipeline is deterministic. Also route the notification-exit-code mismatch to the record: background make reported exit 0 twice while make actually failed -- do not trust bg exit codes for make pipelines, read the output tail.