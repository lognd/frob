---
id: T-1373
title: 'make coverage is red: nested coverage subprocess leak and the T-1333 CSafeLoader
  test'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/unit/test_makefile_coverage.py
- tests/unit/test_ticket_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
- tests/unit/test_ticket_store.py::TestYamlLoader::test_prefers_csafeloader_when_libyaml_present
designated_repro_test: null
acceptance:
- text: GIVEN a full make coverage run WHEN the suite completes THEN tests/unit/test_makefile_coverage.py
    and tests/unit/test_ticket_store.py report no failures
  evidence:
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
  - tests/unit/test_ticket_store.py::TestYamlLoader::test_prefers_csafeloader_when_libyaml_present
evidence_changes:
- old_node: tests/unit/test_makefile_coverage.py::TestCombineRecoversDisjointSessions::test_two_disjoint_sessions_combine_to_full_coverage
  new_node: tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests (924->195
    lines); this citation''s underlying claim survives against the new native_coverage_refresh
    implementation and is proven by the successor node. Shared claim: a crashed/lost
    worker session does not lose coverage data -- the serial-retry recovery path still
    produces full coverage.xml.'
  actor: logan
  at: '2026-08-16'
- old_node: tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_combine_then_xml_survives_a_stale_fixture_path
  new_node: tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests. Shared
    claim: the coverage.xml step is always invoked with -i/--ignore-errors so a torn-down/stale
    source path does not abort the run (T-1320). native_coverage_refresh''s coverage-xml
    call unconditionally passes ''coverage xml -i'' per its own T-1320 comment, exercised
    end to end by this node.'
  actor: logan
  at: '2026-08-17'
threat: null
component: null
anchor: false
anchor_reason: null
---
Found 2026-08-01 by the coordinator's full make coverage run, which the gates stage never exercises (frob check --only gates skips tests). Two distinct causes. (1) test_two_disjoint_sessions_combine_to_full_coverage and test_combine_then_xml_survives_a_stale_fixture_path spawn a nested 'coverage run' subprocess; under an outer make coverage the parent's COVERAGE_* environment leaks into the child and the nested run exits 1. The subprocess needs a coverage-clean env. (2) test_prefers_csafeloader_when_libyaml_present predates T-1333, which deliberately falls back to SafeLoader whenever a coverage tracer is active -- so the assertion is now false under coverage by design. The test must condition on the tracer the same way the fix does.

## Done report

`make coverage` was red for two unrelated reasons, neither of which the
gates stage can see (`frob check --only gates` skips the tests stage
entirely, so main reported 0 errors while the coverage recipe failed).

1. Nested-coverage env leak. `test_two_disjoint_sessions_combine_to_full_
   coverage` and `test_combine_then_xml_survives_a_stale_fixture_path`
   drive real `coverage run` child processes. They passed no `env=`, so
   under an outer `make coverage` the parent's `COVERAGE_FILE` and
   `COVERAGE_PROCESS_START` were inherited: the child measured into the
   parent's data file and the `--append` session exited 1. Added
   `_coverage_clean_env()`, which strips every `COVERAGE_*` variable, and
   routed all seven nested `coverage` subprocesses through it.

2. A test T-1333 invalidated by design. `test_prefers_csafeloader_when_
   libyaml_present` predates T-1333, which deliberately falls back to
   `SafeLoader` whenever a coverage tracer is live. Under coverage the
   unconditional `is yaml.CSafeLoader` assertion was therefore false by
   design, not by defect. The test now pins the no-tracer case explicitly
   rather than inheriting whichever tracer the ambient run installed.

Verified both files green with and without `--cov`.

Not fixed here, filed as T-1374: the fourth failure,
`test_no_reg008_findings_for_check_coverage_yaml`, is a missing
`frob:enforces` edge from T-1266's registry repoint. Its fix touches
`src/frob/gates/**` and `docs/**`, both leased by in-flight agents
(T-1371, T-1372), so it is deliberately deferred rather than raced.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_makefile_coverage.py::TestCombineRecoversDisjointSessions::test_two_disjoint_sessions_combine_to_full_coverage` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_combine_then_xml_survives_a_stale_fixture_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_prefers_csafeloader_when_libyaml_present` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 5 error(s), 1924 warning(s), 695 waived
- error-findings: COV005@tests/unit/test_makefile_coverage.py, E501@/home/logan/projects/frob/src/frob/tickets/_land.py:1231, F401@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:25, F841@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:215, PRE001@tickets/T-1373
