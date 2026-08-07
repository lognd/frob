---
id: T-1335
title: 'make coverage: stamp failure not propagated; stale fixture paths break coverage
  xml'
state: done
kind: bug
origin: agent
created: '2026-07-30'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: 'T-1335''s two acceptance criteria describe Makefile shell behavior (stamp

    failure exit-propagation; coverage.xml surviving a stale fixture path).

    `frob ticket land` refuses to close a code-kind ticket with acceptance

    criteria unbound to evidence, and `--evidence-cmd` is docs-kind only --

    a real pytest node id is required. Adding one small regression test file

    proves both criteria against the actual, current Makefile recipe text

    (no duplicated/drifting reimplementation) rather than leaving them

    structurally unverifiable.

    '
  actor: logan
  at: '2026-07-31'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/unit/test_makefile_coverage.py::TestStampFailurePropagation::test_stamp_failure_after_green_suite_fails_the_recipe
- tests/unit/test_makefile_coverage.py::TestStampFailurePropagation::test_green_suite_and_green_stamp_still_exits_zero
- tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_coverage_xml_invocations_pass_ignore_errors
- tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_combine_then_xml_survives_a_stale_fixture_path
designated_repro_test: null
acceptance:
- text: GIVEN a green suite but a failing stamp-coverage WHEN make coverage runs THEN
    it exits nonzero naming the stamp failure
  evidence:
  - tests/unit/test_makefile_coverage.py::TestStampFailurePropagation::test_stamp_failure_after_green_suite_fails_the_recipe
  - tests/unit/test_makefile_coverage.py::TestStampFailurePropagation::test_green_suite_and_green_stamp_still_exits_zero
- text: GIVEN combined coverage data containing a path with no importable source THEN
    coverage.xml is still produced and the stamp proceeds
  evidence:
  - tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_coverage_xml_invocations_pass_ignore_errors
  - tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_combine_then_xml_survives_a_stale_fixture_path
threat: null
component: null
---
Found during T-1320 (2026-07-30). Three defects in the coverage pipeline: (1) make coverage exits with PYTEST's status only -- a stamp-coverage failure after a green suite yields exit 0 (run 3 printed 'ERROR: stamp-coverage failed: WriteFailed' and still exited 0; only caught by reading the log). The stamp is the whole point of the target; its failure must fail the make. (2) coverage xml died on a stale 'src/demo/__init__.py' entry in the combined data (a test fixture package measured into .coverage via subprocess coverage), producing no coverage.xml at all; recovery was manual 'coverage xml -i'. Either pass ignore-errors in the Makefile or keep fixture paths out of the combined data (source filters in the generated coverage-subprocess.rc). (3) observational: one xdist worker crashed (gw11) on tests/unit/strata/test_conform_eval_needle.py's full-repo scan; the serial rerun caught it, but a repeatedly-crashing heavy test would silently halve coverage data -- consider marking the heaviest real-repo scans for the serial rerun lane. Relates to T-1236 (deflation canary) and T-1205 (coverage as managed derived state).