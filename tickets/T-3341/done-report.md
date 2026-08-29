## Done report

Changed:
tests/unit/test_main_entry.py::TestVerboseFlag.test_dash_v_sets_debug_env_var
tests/unit/test_main_entry.py::TestVerboseFlag.test_dash_dash_verbose_sets_debug_env_var

Root cause: both tests called `monkeypatch.delenv("FROB_VERBOSE", raising=False)`
while the key was already absent. pytest's monkeypatch does not register an
undo action for a delenv on an already-absent key, so it had no way to
revert the later, direct `os.environ["FROB_VERBOSE"] = "1"` write performed
by `_apply_verbose_env_override` (the function under test). That leak
survived test teardown and persisted in the worker process for the rest of
the pytest session, corrupting every subsequent subprocess-based CLI test
that asserts on pure-JSON stdout: `FROB_VERBOSE=1` raises frob's stdout log
handler back to DEBUG, so `doctor: native extension ... available` lines
land ahead of the JSON payload. Confirmed as the root cause of all 4
currently-failing tests/unit/test_parse.py::test_json_output cases
(TestParseCliPytest, TestParseCliTy, TestParseCliClang, TestParseCliJunit)
under a full-suite/xdist run, by bisecting file pairs until the leak
isolated to this exact test class, then reproducing/fixing/re-verifying.

Fix: each leaking test now does `main_module.os.environ.pop("FROB_VERBOSE",
None)` in a `finally` block after asserting. A plain pop is required, not
`monkeypatch.delenv` -- calling `monkeypatch.delenv` on a key that
currently holds a value stages an undo that RE-ADDS that exact value at
teardown, which would silently reintroduce the leak (tried first, verified
wrong via the leak-check probe before landing the pop-based fix).

Evidence: tests/unit/test_main_entry.py::TestVerboseFlag::test_dash_v_sets_debug_env_var
tests/unit/test_main_entry.py::TestVerboseFlag::test_dash_dash_verbose_sets_debug_env_var
tests/unit/test_parse.py::TestParseCliPytest::test_json_output
tests/unit/test_parse.py::TestParseCliTy::test_json_output
tests/unit/test_parse.py::TestParseCliClang::test_json_output
tests/unit/test_parse.py::TestParseCliJunit::test_json_output
All 6 plus the full TestVerboseFlag + test_parse.py files re-run together
(the exact order that reproduced the leak) and pass: 149 passed, 0 failed.

Filed: none

Gates: frob check --ticket T-3341 clean of scope-bound errors (PRE001 stale
sweep cleared via `frob ticket sweep T-3341`; remaining findings in the
report -- ruff-format/ty/frob-cycle/exports/etc -- are pre-existing,
repo-wide, and outside this ticket's scope).

### Changed
```
 tickets/T-3341/ticket.md | 9 ++++++++-
 1 file changed, 8 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestVerboseFlag::test_dash_v_sets_debug_env_var` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestVerboseFlag::test_dash_dash_verbose_sets_debug_env_var` (pytest node id, verified passing when recorded)
- `tests/unit/test_parse.py::TestParseCliPytest::test_json_output` (pytest node id, verified passing when recorded)
- `tests/unit/test_parse.py::TestParseCliTy::test_json_output` (pytest node id, verified passing when recorded)
- `tests/unit/test_parse.py::TestParseCliClang::test_json_output` (pytest node id, verified passing when recorded)
- `tests/unit/test_parse.py::TestParseCliJunit::test_json_output` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 77 error(s), 3950 warning(s), 884 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, COV007@src/frob/tickets/_done_report.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DOC011@docs/guides/release.md, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/doctor.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
