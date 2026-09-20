## Done report

Changed:
src/frob/check/_python.py::_guard_err_result
src/frob/check/_python.py::_run_ruff
src/frob/check/_python.py::_ruff_format_result
src/frob/check/_python.py::_run_ruff_autofix
src/frob/check/_python.py::_run_ty_one
src/frob/check/_native.py::_cmake_configure
src/frob/check/_native.py::_run_cmake_build
src/frob/check/_native.py::_run_clang_tidy_cmake
src/frob/check/_native.py::_run_clang_format
src/frob/check/_native.py::_run_ctest
src/frob/check/_native.py::_run_cargo
src/frob/check/_native.py::_run_cargo_fmt_check
src/frob/check/_native.py::_run_cargo_valgrind
src/frob/check/_native.py::_run_cargo_test
src/frob/check/_ts.py::_run_npx

Evidence:
tests/unit/test_check_tool_unavailable.py::TestRuffUnavailable::test_run_ruff_missing_binary_returns_failing_results
tests/unit/test_check_tool_unavailable.py::TestRuffUnavailable::test_ruff_format_result_missing_binary_returns_failing_result
tests/unit/test_check_tool_unavailable.py::TestTyUnavailable::test_run_ty_missing_binary_returns_failing_result
tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_missing_binary_returns_failing_result
tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_fmt_check_missing_binary_returns_failing_result
tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_test_missing_binary_returns_failing_result
tests/unit/test_check_tool_unavailable.py::TestTscUnavailable::test_run_tsc_missing_npx_returns_failing_result
(--check-repro confirmed test_run_ruff_missing_binary_returns_failing_results genuinely FAILS at parent a01fa88e -- real repro, BUG002 satisfied)

Filed: none

Gates: frob check --ticket T-3818 clean for in-scope files. Remaining FAILs are
pre-existing/out-of-scope: gate:DOC DOC006 (tickets/T-3807/ticket.md, unrelated
ticket), ruff-format (6 files outside scope), ty warnings (2 files outside
scope, tool status still "pass").

### Changed
```
 tickets/T-3818/ticket.md | 8 ++++++++
 1 file changed, 8 insertions(+)
```

### Evidence
- `tests/unit/test_check_tool_unavailable.py::TestRuffUnavailable::test_run_ruff_missing_binary_returns_failing_results` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_tool_unavailable.py::TestRuffUnavailable::test_ruff_format_result_missing_binary_returns_failing_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_tool_unavailable.py::TestTyUnavailable::test_run_ty_missing_binary_returns_failing_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_missing_binary_returns_failing_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_fmt_check_missing_binary_returns_failing_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_test_missing_binary_returns_failing_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_tool_unavailable.py::TestTscUnavailable::test_run_tsc_missing_npx_returns_failing_result` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 1 error(s), 4351 warning(s), 922 waived
- error-findings: DOC006@tickets/T-3807/ticket.md
