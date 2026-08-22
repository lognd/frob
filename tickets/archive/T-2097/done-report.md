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
