## Done report

Resumed from a dead predecessor agent's uncommitted worktree state. Reviewed
and verified the predecessor's 9-file annotation pass (best-effort/never-
fatal boundary catches with debug logging in app/config.py, app/
cycle_runner.py, app/debt_runner.py, app/telemetry.py, arch/__init__.py,
arch/_layering.py, arch/_smells.py, clean/_core.py, __main__.py) as correct
and committed it. Re-acquired the T-1022 lease properly via
`frob ticket start --foreground` (the predecessor's uncommitted
queued->in-progress ledger line was discarded and replayed through the CLI
instead).

Live EXHAUST001/002 count at pickup: 186 (predecessor's pass had already
closed 4 of the original 190). Added a second pass closing all 10 sites in
src/frob/check/_native.py: introduced a shared
process/parsers/common.py::tool_crash_result() helper (mirrors the existing
tool_unavailable_result/tool_disabled_result doctrine) and routed every
cmake/clang-tidy/clang-format/ctest/cargo runner's subprocess-spawn and
report-parse steps through it, so an unexpected crash surfaces as a typed
failing ToolResult instead of an escaping exception -- the idiomatic fix for
this module (it already returns ToolResult as its error-as-values type at
every other failure boundary), not a blanket swallow. Added regression
coverage for the new helper and two of the newly-typed crash paths
(tests/unit/test_check_tool_unavailable.py).

Final live count: 176 residual sites (122 EXHAUST001, 54 EXHAUST002),
confirmed via `frob check --only exhaustive_handling --json`. This is a
coherent partial: the remaining sites are spread across ~40 files (gates/
__init__.py 17, gates/_coverage.py 8, dup/_pipeline.py 6, tickets/_leases.py
6, and many smaller clusters) too large to honestly clear in this pass.
Filed T-1056 as the follow-up with the exact residual
breakdown and the tool_crash_result precedent to reuse.

### Changed
```
 docs/modules/app.md                          |   4 +-
 docs/modules/arch.md                         |   5 +-
 docs/modules/process.md                      |   3 +
 src/frob/__main__.py                         |  10 ++
 src/frob/app/config.py                       |  39 ++++--
 src/frob/app/cycle_runner.py                 |  34 ++---
 src/frob/app/debt_runner.py                  |   7 +-
 src/frob/app/telemetry.py                    |   1 +
 src/frob/arch/__init__.py                    |   6 +-
 src/frob/arch/_layering.py                   |  25 ++--
 src/frob/arch/_smells.py                     |  35 +++--
 src/frob/check/_native.py                    |  72 ++++++++--
 src/frob/clean/_core.py                      |  18 ++-
 src/frob/graph/dsl.py                        |  11 +-
 src/frob/process/parsers/common.py           |  22 +++
 tests/unit/test_check_tool_unavailable.py    |  50 +++++++
 tests/unit/test_cycle_runner_process_path.py | 191 +++++++++++++++++++++++++++
 tests/unit/test_main_entry.py                |  47 +++++++
 tickets.md                                   | 140 +++++++++++++++++++-
 19 files changed, 645 insertions(+), 75 deletions(-)
```

### Evidence
- `tests/unit/test_check_tool_unavailable.py::TestToolCrashResult::test_shape_is_a_failing_diagnostic` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_tool_unavailable.py::TestNativeCrashIsTypedResult::test_run_cargo_unexpected_crash_returns_failing_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_tool_unavailable.py::TestNativeCrashIsTypedResult::test_run_cargo_test_unexpected_crash_returns_failing_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_prints_clean_message_and_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_logs_with_exc_info` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_file_in_skipped_dir_is_not_added` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_file_matching_exclude_glob_is_not_added` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_python_file_with_matching_lang_is_added` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_python_file_wrong_requested_lang_is_skipped_after_node_add` (pytest node id, verified passing when recorded)
- `tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_nonmatching_nonempty_exclude_globs_does_not_short_circuit` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_cpp_file_requested_as_cpp_is_scanned_as_cpp` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_cpp_file_requested_as_python_is_not_scanned` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_process_path.py::TestProcessPathGating::test_plain_python_file_default_lang_is_scanned` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 14 evidence id(s))
- gates: 4 error(s), 8115 warning(s), 374 waived
- error-findings: DOC002@src/frob/gates/__init__.py, DOC002@src/frob/serve/_tools.py, INV006@src/frob/gates/_gate_cache.py, TEST001@src/frob/gates/_gate_cache.py
