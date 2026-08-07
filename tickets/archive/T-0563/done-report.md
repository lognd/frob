## Done report

Migrated the 14 bare print/stdout call sites named in T-0459's Done report
(check_runner, clean_runner, debt_runner, doctor_runner, gitlog_runner,
registry_runner, test_runner) to `frob.render`/`_log.info`, keeping every
`--json` payload byte-stable (same content, same trailing newline; INFO
records format as bare message text per `frob.logging.formatter`). Two
runners (`debt_runner`, in a follow-up during test fixing) needed
`quiet_stdout_logs` wrapped around their computation so graph-build
INFO/DEBUG chatter cannot land ahead of the JSON payload on the shared
stdout-bound logger channel -- `check_runner`'s json path was already safe
(its `_stdout_log_ctx` restores the handler level before
`_report_check_result` runs). Promoted RENDER001 from WARN to ERROR
severity in `src/frob/gates/_render_lint.py` now that the straggler list
is empty. Updated three existing tests (`test_json_mode_prints_json_and_
errors_exit_1`, `test_json_mode_prints_json` in gitlog, `test_json_mode_
lists_debt_entries`) from `capsys` to `caplog`, matching the `frob map`/
`frob dup` `--json`-via-logger test convention already established in this
codebase (the pre-existing tests asserted against `capsys` because the
code they tested used a bare `print`; once migrated to `_log.info`, only
`caplog` observes the payload in a unit test without a configured root
logger, though production output is byte-identical since INFO/DEBUG emit
just the message per `config.toml`'s `_FrobFormatter`).

Ran the full `tests/system/test_cli_check.py` suite and confirmed 10
pre-existing failures (an "unknown project type" / no-git-repo subprocess
environment issue unrelated to this change, confirmed by reverting
check_runner.py alone and re-running one of the failing tests, which still
failed identically against the unmodified file).

### Changed
```
 src/frob/app/check_runner.py          | 21 +++++++++++++--------
 src/frob/app/clean_runner.py          |  3 ++-
 src/frob/app/debt_runner.py           | 25 ++++++++++++++++++-------
 src/frob/app/doctor_runner.py         | 11 +++++++----
 src/frob/app/gitlog_runner.py         | 17 +++++++++++++++--
 src/frob/app/registry_runner.py       |  5 +++--
 src/frob/app/test_runner.py           | 23 +++++++++++++++--------
 src/frob/gates/_render_lint.py        | 23 ++++++++++-------------
 tests/test_debt_runner.py             | 15 ++++++++++++---
 tests/unit/test_app_runners.py        | 17 ++++++++++++-----
 tests/unit/test_app_runners_batch6.py | 12 ++++++++----
 tickets.md                            |  9 +++++++--
 12 files changed, 122 insertions(+), 59 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_json_mode_prints_json_and_errors_exit_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestGitlogRunner::test_json_mode_prints_json` (pytest node id, verified passing when recorded)
- `tests/test_debt_runner.py::TestDebtRunner::test_json_mode_lists_debt_entries` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRenderLintGate::test_bare_print_fires` (pytest node id, verified passing when recorded)
