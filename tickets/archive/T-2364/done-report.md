## Done report

Changed:
- src/frob/check/_python.py::_cycle_diags -- CYCLE001 code + deterministic
  representative file (lowest-sorted node) attached to each import-cycle
  Diagnostic; message content unchanged.
- src/frob/check/_python.py::_cycle_representative_file -- new helper,
  deterministic identity anchor.
- tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths -- three
  new tests: must-fire identity check, cross-run determinism check, and a
  negative control (clean tree yields zero diagnostics).

Evidence:
- tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_cycle_finding_has_identity_not_none
  (designated repro; FAILED_AT_PARENT confirmed at 44bf34162, the
  test-only commit, via `frob ticket evidence --check-repro`)
- tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_cycle_finding_identity_deterministic_across_runs
- tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_no_cycle_produces_no_diagnostics

Filed: none -- no out-of-scope work found. The producer was located in
src/frob/check/_python.py (not src/frob/gates/ as the ticket's own
investigation note guessed); scope was narrowed to drop the leased
gates/__init__.py and cycle/graph.py globs and add the real files.

Gates: uv run frob check pending at land time; targeted pytest run
(tests/unit/test_check.py -k cycle) is 9 passed, 0 failed locally.
