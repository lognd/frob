## Done report

Changed:
- src/frob/app/perf_runner.py::_read_perf_file_text (new)
- src/frob/app/perf_runner.py::_resolve_perf_format (new)
- src/frob/app/perf_runner.py::_parse_perf_text_or_exit (new)
- src/frob/app/perf_runner.py::_collect_stacks_from_file (body delegates to the three new helpers; unchanged behavior)
- src/frob/gates/__init__.py::_stamp_worker_stdout_log_level_env (new)
- src/frob/gates/__init__.py::_stamp_worker_lock_keys_env (new)
- src/frob/gates/__init__.py::_open_process_pool (body delegates the two env-marker stamps to the new helpers; T-0947 forkserver-preload path and T-0982 lock-key-stamp-before-pool-construction order both preserved unchanged)
- frob.toml: `[gates.severity] ARCH103 = "error"` (promoted)

Disposition per finding (both resolved by real extraction, no waiver):
- `_collect_stacks_from_file` (3 decision points: `cfg.perf_file is None`,
  a `try/except OSError`, `result.is_err`, plus the `cfg.perf_format or
  detect_collector_format(...)` boolean-operator branch and a `str(file)`
  format call) -- split into `_read_perf_file_text` (read-or-exit, 0
  branches of its own since `except` clauses aren't counted as decision
  points by ARCH103's proxy), `_resolve_perf_format` (1 branch: the `or`),
  and `_parse_perf_text_or_exit` (1 branch: `result.is_err`). Each helper's
  own decision count now sits below ARCH103's `min_decision_points=2`
  threshold, so none trigger regardless of the I/O/formatting calls they
  still contain individually.
- `_open_process_pool` (4 decision points across the two env-marker
  stamps plus the forkserver branch) -- split the two independent stamps
  (`_WORKER_STDOUT_LOG_LEVEL_ENV`, `_INHERITED_LOCK_KEYS_ENV`) into
  `_stamp_worker_stdout_log_level_env` and `_stamp_worker_lock_keys_env`,
  each with exactly 1 branch of its own. `_open_process_pool` itself now
  has only 1 remaining branch (`ctx.get_start_method() == "forkserver"`),
  below threshold. T-0947's forkserver+preload behavior and T-0982's
  stamp-before-pool-construction ordering are both unchanged -- the two
  stamp calls still run, in the same order, before `ProcessPoolExecutor`
  is constructed.

Promotion: `[gates.severity] ARCH103 = "error"` in frob.toml. Verified via
a fresh, unscoped `uv run frob check --only gates-native --json`: 22
ARCH103 findings total repo-wide, all carrying a real `frob:waive
ARCH103` (T-0977's prior burn-down); 0 live/unwaived findings anywhere,
including the two named sites. `frob check --ticket T-0990` (full gate
pass, scoped) also passes clean (`gate:ARCH 0 errors, 0 warnings, 51
waived`; `gate-summary 0 errors`).

Evidence:
- tests/system/test_cli_perf.py::TestPerfCollect::test_collect_resolves_a_real_python_hot_frame
- tests/system/test_cli_perf.py::TestPerfCollect::test_collect_json_output_is_valid_json
- tests/system/test_cli_perf.py::TestPerfCollect::test_collect_autodetects_cpuprofile_format
- tests/test_gates.py::TestProcessPoolGates::test_open_process_pool_preloads_forkserver_when_available
- tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_real_pool_worker_under_parent_shared_holder_completes
- tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_independent_process_without_marker_still_blocks

All 6 recorded via `frob ticket evidence T-0990` and re-verified passing
(python exit=0, 7 tests via `frob test --base main`'s touched-set run,
which also pulled in `tests/integration/test_interfaces.py::TestInterfaces::test_app_runner_map`
and `tests/test_gates.py::test_gates_run_gates_integration`).

Filed: none.

Gates: `frob check --ticket T-0990` clean (0 errors); `frob test --base
main` PASS (exit=0, 7/7 tests); ruff-check clean after fixing 5 E501s
introduced by the new frob:tests directive comments (noqa: E501 added to
the long directive lines, matching this file's existing convention for
long frob:tests comments elsewhere).

### Changed
(no changed files detected)

### Evidence
- `tests/system/test_cli_perf.py::TestPerfCollect::test_collect_resolves_a_real_python_hot_frame` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_perf.py::TestPerfCollect::test_collect_json_output_is_valid_json` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_perf.py::TestPerfCollect::test_collect_autodetects_cpuprofile_format` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProcessPoolGates::test_open_process_pool_preloads_forkserver_when_available` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_real_pool_worker_under_parent_shared_holder_completes` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_independent_process_without_marker_still_blocks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 4886 warning(s), 318 waived
- error-findings: none (measured, zero errors)
