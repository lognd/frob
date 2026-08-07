---
id: T-1235
title: 'coverage attribution fix: subprocess rc + multiprocessing concurrency'
state: done
kind: bug
origin: agent
created: '2026-07-29'
priority: critical
blocked_by:
- T-1395
parent: T-0969
tier: ticket
sprint: null
scope:
- Makefile
- pyproject.toml
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_uses_absolute_source_and_data_file
- tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_declares_multiprocessing_and_sigterm
- tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_remaps_paths_back_to_source
- tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_pyproject_declares_concurrency_and_sigterm
- tests/unit/test_coverage_attribution_lock_t1395.py::TestCoverageAttributionLockStaysNonZero::test_t1395_named_modules_are_nonzero_in_committed_lock
designated_repro_test: null
acceptance:
- text: GIVEN make coverage runs THEN a generated .frob/coverage-subprocess.rc (absolute
    source and data_file, branch/parallel/relative_files/sigterm true, concurrency
    multiprocessing+thread, disable_warnings no-data-collected, paths remap) is what
    COVERAGE_PROCESS_START points at, and zero .coverage.* files are stranded outside
    repo root after the run
  evidence:
  - tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_uses_absolute_source_and_data_file
  - tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_declares_multiprocessing_and_sigterm
  - tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_remaps_paths_back_to_source
- text: GIVEN pyproject [tool.coverage.run] THEN concurrency multiprocessing+thread
    and sigterm true are set so in-process gate-pool execution is recorded
  evidence:
  - tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_pyproject_declares_concurrency_and_sigterm
- text: GIVEN the corrected full run THEN previously-exercised-but-zero symbols (excludes.py,
    doctor.py, serve/, __main__.py) report real coverage and the TEST005 count reflects
    it
  evidence:
  - tests/unit/test_coverage_attribution_lock_t1395.py::TestCoverageAttributionLockStaysNonZero::test_t1395_named_modules_are_nonzero_in_committed_lock
threat: null
component: null
---
T-0969 diagnosis 2026-07-29: fresh coverage RAISED TEST005 to 1357; staleness was not the inflation. Loss A: CLI subprocesses measure nothing (relative source vs child cwd) and strand data files in child cwds (626 stranded, 100% of 120 sampled empty). Loss B: ProcessPoolExecutor gate workers unrecorded. Verified experiment: corrected rc moved excludes.py 51->97, doctor 33->86, 81 of 103 zero-modules gained data; merged count 1357->1175 from a partial subset alone.