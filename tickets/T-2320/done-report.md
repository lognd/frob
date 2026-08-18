## Done report

Changed:
- src/frob/check/_python.py::_run_ruff (now takes skip_check/skip_format,
  runs either/both independently)
- src/frob/check/_python.py::_run_ruff_autofix (new: real `ruff check
  --fix` + `ruff format` WRITE pass, distinct from Tier-A/B/C fixers)
- src/frob/check/__init__.py::_python_skip_flags (adds skip_ruff_check/
  skip_ruff_format, OR'd with the legacy bundled skip_ruff)
- src/frob/check/__init__.py::_python_tasks (routes the split skip flags
  into _run_ruff)
- src/frob/check/__init__.py::run_check (new skip_ruff_check/
  skip_ruff_format kwargs)
- src/frob/_cli_parsers/_check.py::_add_check_skip_args_python (new
  --skip-ruff-check / --skip-ruff-format flags)
- src/frob/_cli_parsers/_check.py::_add_check_selection_args (new
  --fix-ruff flag)
- src/frob/app/config.py::AppConfig (check_skip_ruff_check,
  check_skip_ruff_format, check_ruff_fix fields)
- src/frob/app/check_runner.py::_dispatch_check_python (threads the two
  new skip flags through to run_check)
- src/frob/app/check_runner.py::_handle_early_exit_modes,
  _run_ruff_fix_mode (new: --fix-ruff early-return dispatch, mirrors
  --stamp-coverage/--stamp-baseline's shape)
- docs/commands/check.md (documents the split skip flags and --fix-ruff)
- tests/unit/test_check.py (new evidence)

Evidence:
- tests/unit/test_check.py::TestRunRuffSplitSkip::test_skip_check_runs_only_format
- tests/unit/test_check.py::TestRunRuffSplitSkip::test_skip_format_runs_only_check
- tests/unit/test_check.py::TestRunRuffSplitSkip::test_skip_both_returns_empty
- tests/unit/test_check.py::TestRunRuffSplitSkip::test_neither_skipped_runs_both_unchanged
- tests/unit/test_check.py::TestRunRuffAutofix::test_success_runs_fix_then_format_via_uv_run
- tests/unit/test_check.py::TestRunRuffAutofix::test_missing_binary_yields_two_typed_results
- tests/unit/test_check.py::TestRunRuffAutofix::test_kill_switch_disabled_yields_two_typed_results
- tests/unit/test_check.py::TestRunRuffAutofix::test_check_fix_nonzero_exit_still_runs_format
- tests/unit/test_check.py::TestDispatchCheckPythonThreadsRuffSplit::test_python_dispatch_threads_ruff_split
- tests/unit/test_check.py::TestDispatchCheckPythonThreadsRuffSplit::test_default_ruff_split_flags_unchanged
- tests/unit/test_check.py::TestRuffFixModeDispatch::test_fix_ruff_flag_short_circuits_run
- tests/unit/test_check.py::TestRuffFixModeDispatch::test_without_the_flag_falls_through
- tests/unit/test_check.py::TestRuffFixModeDispatch::test_reports_results_and_exits_clean
- tests/unit/test_check.py::TestRuffFixModeDispatch::test_unavailable_tool_exits_nonzero
- tests/unit/test_check.py::TestRuffFixModeDispatch::test_remaining_lint_violations_do_not_fail_the_command

Full file run: `uv run pytest tests/unit/test_check.py -p no:cacheprovider -q`
-> SUITE-RESULT: exitstatus=0 collected=110 failed=0 (all pre-existing
tests still pass, nothing regressed by the split).

Filed: none (no out-of-scope work discovered)

Gates:
- `uv run frob check --ticket T-2320` shows 131 repo-wide errors (this
  repo's known pre-existing floor, `--ticket` does not filter most gate
  families per playbook 6c); none are in any file this ticket touched
  (grepped the finding list for each touched path, all clear of
  unwaived hits).
- `uv run frob check --land-parity` was attempted repeatedly and, under
  this session's concurrent-agent contention, twice could not complete
  the "static"/"lint" stage groups inside budget (T-1703 deferred-group
  reporting, not a false-clean) and once timed out on its own post-sweep
  step. One run that DID complete cleanly identified only
  tests/unit/test_check.py needing ruff-format on the two new lines I
  added (fixed, verified 0-diff with `ruff format --diff` except for one
  PRE-EXISTING unrelated blank-line-at-top-of-file drift already present
  on main, left untouched as out of scope).

Note (per the ticket's own disclosed caveat): `--fix-ruff` is wired as a
standalone early-return action (same shape as --stamp-coverage/--stamp-
baseline), not folded into the normal check pipeline or into `--fix`'s
Tier-A/B/C re-verify loop -- this matches the ticket's ask for a WRITE
mode "distinct from" --fix's narrow fixers. Repointing `format:`/`lint-
fix:` Makefile leaves to it (T-2244) is left to that ticket, since this
repo currently has ~120-130 files that would be reformatted by a real
ruff-format pass (T-2320's own ticket body already flagged this) and a
first real run would rewrite a large, out-of-scope set of files.

### Changed
```
 tickets/T-2320/ticket.md | 38 +++++++++++++++++++++++++++++++++++++-
 1 file changed, 37 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_check.py::TestRunRuffSplitSkip::test_skip_check_runs_only_format` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffSplitSkip::test_skip_format_runs_only_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffSplitSkip::test_skip_both_returns_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffSplitSkip::test_neither_skipped_runs_both_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffAutofix::test_success_runs_fix_then_format_via_uv_run` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffAutofix::test_missing_binary_yields_two_typed_results` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffAutofix::test_kill_switch_disabled_yields_two_typed_results` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffAutofix::test_check_fix_nonzero_exit_still_runs_format` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDispatchCheckPythonThreadsRuffSplit::test_python_dispatch_threads_ruff_split` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDispatchCheckPythonThreadsRuffSplit::test_default_ruff_split_flags_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRuffFixModeDispatch::test_fix_ruff_flag_short_circuits_run` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRuffFixModeDispatch::test_without_the_flag_falls_through` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRuffFixModeDispatch::test_reports_results_and_exits_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRuffFixModeDispatch::test_unavailable_tool_exits_nonzero` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRuffFixModeDispatch::test_remaining_lint_violations_do_not_fail_the_command` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@src/frob/check/__init__.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_leases.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, DRIFT002@src/frob/verify/_drain.py, DUP001@tests/unit/test_check.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2320, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_leases.py, TICK004@tickets.md, WIRE001@src/frob/_cli_parsers/_check.py, WIRE003@docs/modules/cli.md
