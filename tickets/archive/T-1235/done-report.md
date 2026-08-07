## Done report

Fix implemented on the w16b-coverage branch and landed onto main via T-1236's branch merge (commit 9614f1a5 -- the whole w16b-coverage branch, including this ticket's Makefile/pyproject/rc-generation changes, arrived in that land). All four bound evidence tests (tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware) pass on main post-land. The generated .frob/coverage-subprocess.rc now uses absolute source/data_file paths, declares concurrency = multiprocessing+thread with sigterm true, and remaps paths back to source, so subprocess and pool-worker coverage attribute correctly instead of being dropped. Closed on main directly (not via its own land) because the content had already merged through the sibling ticket's land; a solo re-land of this ticket has an empty diff.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_uses_absolute_source_and_data_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_declares_multiprocessing_and_sigterm` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_remaps_paths_back_to_source` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_pyproject_declares_concurrency_and_sigterm` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 254 warning(s), 745 waived
- error-findings: none (measured, zero errors)
