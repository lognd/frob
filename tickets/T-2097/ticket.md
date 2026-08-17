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
land_commit: null
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

## Done report

### Changed
tests/unit/test_check_budget.py::TestRunBudgetedCheck.test_budget_json_stdout_is_pure_parsable_json
tests/unit/test_app_runners.py::TestDesignRunner.test_exports_subcommand_delegates_to_exports_runner

### Evidence
tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_budget_json_stdout_is_pure_parsable_json
tests/unit/test_app_runners.py::TestDesignRunner::test_exports_subcommand_delegates_to_exports_runner

Both re-verified: full test_check_budget.py (14 passed), full
test_app_runners.py (67 passed).

### Investigation and verdict
Measured, not assumed: real `uv run frob check <tmpdir> --budget 5 --json`
via a subprocess AND a bare in-process `check_runner.run()` call outside
pytest both emit the JSON payload cleanly on real stdout. The payload is
correctly produced in production. This is NOT a regression of T-1703's
own fix.

Root cause: `src/frob/logging/logger.py::_init` (T-1621, landed AFTER
T-1703) sets `cfg["root"]["handlers"] = []` whenever `"pytest" in
sys.modules`, to stop every frob log record printing twice in pytest's
own report (frob's own StreamHandler line plus pytest's independent
`LogCaptureHandler` "Captured log call"). Side effect: under pytest, NO
frob log record -- including a `--json` payload emitted via
`_log.info(json.dumps(...))` per RENDER001 (bare `print` forbidden even
for `--json`) -- ever reaches a real stdout handler; it is observable
only via `caplog`. `capsys` cannot see it, structurally, independent of
whether the underlying fix is correct.

These two tests were the last stragglers still asserting `capsys` for a
logger-routed JSON payload; ~15 other tests already use the established
`caplog`-based `--json`-via-logger convention this repo adopted at T-1621
land time (`TestGitlogRunner.test_json_mode_prints_json`'s own docstring
names the convention explicitly). `test_exports_subcommand_delegates_to_
exports_runner`'s own waive comment even already claimed the "real-
fixture-plus-caplog shape" while the code underneath still used `capsys`
-- these two tests were never updated when T-1621 landed.

Fix: rewrote both assertions against `caplog`, preserving the original
intent (a single record whose full text parses as valid JSON / contains
the expected content) rather than weakening either assertion.

### Gates
`frob ticket evidence T-2097 --check-repro` on both node ids: both
FAILED_AT_PARENT at 0f004f02dfdd0e5e4bb9cf7863a18882eb7f2d86 (genuine
repro, confirmed BEFORE the fix commit). Fix landed as a separate commit
after the repro-confirming parent per playbook 7b.

Filed: none (this was already GROUP 1's own ticket; no new out-of-scope
findings)

### Changed
```
 tests/unit/test_app_runners.py  | 15 +++++++++++----
 tests/unit/test_check_budget.py | 25 +++++++++++++++++++++----
 tickets/T-2097/ticket.md        | 13 +++++++++----
 3 files changed, 41 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_budget_json_stdout_is_pure_parsable_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestDesignRunner::test_exports_subcommand_delegates_to_exports_runner` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: PRE001@tickets/T-2097
