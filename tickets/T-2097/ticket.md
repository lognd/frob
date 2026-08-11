---
id: T-2097
title: Two --json CLI tests assert capsys instead of caplog, broken by T-1621's pytest
  handler skip
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/unit/test_check_budget.py
- tests/unit/test_app_runners.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_budget_json_stdout_is_pure_parsable_json
- tests/unit/test_app_runners.py::TestDesignRunner::test_exports_subcommand_delegates_to_exports_runner
designated_repro_test: tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_budget_json_stdout_is_pure_parsable_json
acceptance:
- text: Given frob check --budget --json's payload logged via _log.info, when test_budget_json_stdout_is_pure_parsable_json
    runs under pytest, then it asserts against caplog (matching the repo's established
    --json-via-logger convention) and parses cleanly as JSON
  evidence:
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_budget_json_stdout_is_pure_parsable_json
- text: Given frob design --command exports --json's payload logged via _log.info,
    when test_exports_subcommand_delegates_to_exports_runner runs under pytest, then
    it asserts against caplog and finds the expected content
  evidence:
  - tests/unit/test_app_runners.py::TestDesignRunner::test_exports_subcommand_delegates_to_exports_runner
threat: null
component: null
anchor: false
anchor_reason: null
---
Two tests assert a --json/--budget CLI payload against `capsys.
readouterr().out` and fail: `tests/unit/test_check_budget.py::
TestRunBudgetedCheck::test_budget_json_stdout_is_pure_parsable_json` and
`tests/unit/test_app_runners.py::TestDesignRunner::
test_exports_subcommand_delegates_to_exports_runner`.

Root cause investigated end to end (real subprocess spawn of
`uv run frob check <tmp> --budget 5 --json`, and a direct in-process
`check_runner.run()` call outside pytest): the JSON payload DOES land on
real stdout in production. Both fail ONLY under pytest.

`src/frob/logging/logger.py::_init` (landed by T-1621, AFTER T-1703, so
T-1703's own tests were never re-verified against it) sets
`cfg["root"]["handlers"] = []` whenever `"pytest" in sys.modules`, to stop
every frob log record appearing twice in pytest's own report (frob's own
StreamHandler line plus pytest's separate `LogCaptureHandler` "Captured
log call"). That is deliberate and correct for the double-print problem,
but its side effect is that under pytest NO frob log record -- including
a `--json` payload emitted via `_log.info(json.dumps(...))`, per RENDER001
which forbids a bare `print` even for `--json` -- ever reaches a real
stdout handler at all; it is observable only via `caplog`. `capsys` can no
longer see it, structurally, regardless of T-1703's own fix being correct.

This is NOT a production regression of T-1703. It is these two tests
never being updated to the `caplog`-based assertion convention this same
repo already established for exactly this shape at T-1621 land time
-- see `tests/unit/test_app_runners.py::TestGitlogRunner::
test_json_mode_prints_json`'s own docstring: "JSON mode logs the JSON
rendering ... via `_log.info`/RENDER001, matching `frob map`/`frob dup`'s
`--json`-via-logger convention -- assert against `caplog`" -- and the
~15 other `caplog`-based `*_json_mode*` tests already following it
repo-wide. These two tests are the last stragglers still asserting
`capsys` for a logger-routed JSON payload.

Fix: rewrite both assertions to use `caplog` (matching the established
convention), preserving the original intent (a single record whose full
text parses as valid, uncorrupted JSON) rather than weakening it.