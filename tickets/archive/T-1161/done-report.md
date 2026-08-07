## Done report

Two-part honest-failure fix from the venv-shim incident (2026-07-28: a
cross-worktree `uv` operation rewrote the root venv's `pytest` shim
shebang; once the other worktree was removed, `uv run pytest` broke and
the coverage gate emitted 6219 COV003s -- one per archived evidence id --
instead of naming the real, single cause).

(a) `frob doctor` now scans `.venv/bin/` entrypoint scripts
(`scan_venv_shims`/`VenvShimDrift` in `src/frob/doctor.py`) for a shebang
pointing at a python interpreter outside this checkout's own venv, and
folds any finding into the overall healthy/remediation verdict with the
exact `uv sync --reinstall-package <name>` repair command (or `make
install-tool`).

(b) `collect_python_tests` (`src/frob/testing/_collect.py`) now records a
human-readable failure detail (argv, exit code, `excerpt`-truncated
stderr) whenever its outer `pytest --collect-only` fails, readable via
the new `python_collection_failure_detail()`. Its `Result[CollectedTests,
TestingError]` contract is unchanged -- this is an additive, separate
read. `run_gates`' `_load_tests` threads that detail through
`_GateInputs.python_collection_failed` into `coverage_gate`, which now
reports exactly ONE COV003 naming the collection failure instead of
iterating every DONE ticket's evidence and reporting each as
independently unresolved (mirrors T-1148's NATIVE001 fail-fast design:
detect the environment fault once, loudly, with the repair command).

Scope was extended beyond the ticket's original declaration (each via
`frob ticket scope --add` with a reason) to reach the coverage-gate half
of the fix (`src/frob/gates/__init__.py`, `tests/test_gates.py`), the
doctor-CLI test suite (`tests/system/test_cli_doctor.py`), doc anchors
(`docs/guides/install.md`, `docs/modules/testing.md`,
`docs/modules/gates.md`), and `design/frob.strata` (SYS104/SELFAUDIT001
interface= sync via `frob sys sync-interface`, plus the derived
`frob.lock` ack file) -- the ticket's declared scope only covered the
collector/doctor side, not the gate-wiring side the acceptance criteria
require.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_testing_collect.py::TestPythonCollectionFailureDetail::test_none_before_any_call` (pytest node id, verified passing when recorded)
- `tests/test_testing_collect.py::TestPythonCollectionFailureDetail::test_outer_collection_failure_records_detail_with_stderr_tail` (pytest node id, verified passing when recorded)
- `tests/test_testing_collect.py::TestPythonCollectionFailureDetail::test_successful_collection_clears_a_prior_failure_detail` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_flags_shebang_outside_venv` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_clean_shebang_reports_nothing` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorVenvShims::test_no_venv_directory_reports_nothing` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_load_tests_captures_python_collection_failure_detail` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_coverage_gate_reports_one_violation_on_python_collection_failure` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 0 error(s), 1231 warning(s), 503 waived
- error-findings: none (measured, zero errors)
