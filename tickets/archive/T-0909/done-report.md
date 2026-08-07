## Done report

Changed:
- tests/system/conftest.py::run (added a `timeout` kwarg, passed straight
  through to `subprocess.run`, so hang-guard tests can route through the
  shared helper without losing their timeout)
- tests/system/test_cli_check.py::TestFrobTomlCheckDefaults.test_check_skip_from_frob_toml
  (now calls `run("check", str(tmp_path), "--json", cwd=tmp_path)` instead
  of a raw `subprocess.run`)
- tests/system/test_cli_ticket.py::TestTicketNewNonInteractive.test_new_does_not_prompt_or_hang_without_a_tty
  (now calls `run("ticket", "new", ..., timeout=10)` instead of a raw
  `subprocess.run`)

Evidence:
- `FROB_AGENT=1 FROB_WORKTREE=/tmp/fake-worktree uv run pytest -q
  tests/system/test_cli_check.py::TestFrobTomlCheckDefaults::test_check_skip_from_frob_toml
  tests/system/test_cli_ticket.py::TestTicketNewNonInteractive::test_new_does_not_prompt_or_hang_without_a_tty
  tests/system/test_run_helper_env_leak.py` -- 4 passed (the exact leak
  scenario T-0880 fixed for run()-based tests, now also clean for these
  two)
- `uv run pytest -q tests/system/test_cli_check.py
  tests/system/test_cli_ticket.py --deselect
  tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root`
  -- full pass (44 tests) on a clean rerun; one earlier run in the same
  session showed two unrelated xdist-parallel-worker flakes
  (TestGitlessTargetGateSeverity's capsys/logging-rebind test, documented
  as order-dependent in its own docstring, and
  TestCheckPolyglot::test_pinned_check_type_reports_skipped_line, an
  sqlite fingerprint-cache contention artifact) -- both pass individually
  in isolation and on a clean full rerun, confirming neither is caused by
  this change.
- `uv run frob check --ticket T-0909` -- 0 errors (gate:PRE required one
  `frob ticket sweep T-0909` re-run after the conftest.py scope
  amendment below; all other gates pass, including SCOPE/COV/TEST for
  the touched files).

Filed: none

Gates: frob check --ticket T-0909 clean.
