## Done report

Changed:
tests/unit/test_app_runners_process.py::TestOpsRunnerProcessDispatch (5 AppConfig call sites)
tests/unit/test_pytest_spawn_env_wiring.py::TestMutateRunnerWiring / TestPerfRunnerProfileWiring (3 AppConfig call sites)

Root cause: these 8 call sites passed AppConfig(command="ops"/"mutate"/"perf", ...) but
AppConfig has no `command` field -- the real field is `subcommand: Subcommand | None`.
Fixed by importing Subcommand and passing subcommand=Subcommand.ops / .mutate / .perf,
then ran ruff format on both files (4 call sites needed line wrapping after the longer
kwarg name).

Evidence:
- ty check --python-platform {linux,win32,darwin} src tests/unit/test_app_runners_process.py
  tests/unit/test_pytest_spawn_env_wiring.py: unknown-argument count 8->0 per platform,
  24->0 total, all three platforms clean.
- pytest tests/unit/test_app_runners_process.py tests/unit/test_pytest_spawn_env_wiring.py -q:
  14 passed, 0 failed.
- frob check --ticket T-3257 --only scope --only drift --only coverage --only test:
  gate:SCOPE pass (0 errors), gate:TEST pass (0 errors); gate:COV (36 errors, repo-wide
  pre-existing debt, none in the two touched files) and gate:DRIFT (53 errors, repo-wide,
  owned by another series per task background) unaffected by this change per the
  --ticket NOTE (those counts are repo-wide, not ticket-scoped).
- frob check --ticket T-3257 --only fmt --only affect_drift --only prework --only ruff --only ty:
  ruff-check pass; ruff-format FAIL is 80 files repo-wide, neither touched file among them;
  ty tool pass.

Filed: none

Gates: frob check --ticket T-3257 clean on gate:SCOPE and gate:TEST (the two gate
families --ticket actually scopes to this ticket's touched set, per the tool's own
NOTE); repo-wide gate:COV/DRIFT/WAIVE/PRE findings pre-exist this change and are owned
by other series' clusters per task background (DRIFT 53, COV 38).

CI-blocking note (per task instruction): CI's ty gate is `uv run ty check src` (src
only, confirmed via .github/workflows/ci.yml:58 and Makefile SRC var) -- all 24
findings were in tests/, not src/, so this cluster was NOT CI-blocking before the fix.
It is still a real bug (broken/inconsistent test fixtures) worth the one-fix/24-error
ratio, now fixed regardless.

### Changed
```
 tickets/T-3257/ticket.md | 11 ++++++++++-
 1 file changed, 10 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_app_runners_process.py::TestOpsRunnerProcessDelegation::test_process_subcommand_delegates_to_process_runner` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_process.py::TestProcessRunnerReap::test_reap_reports_reaped_pids` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_process.py::TestProcessRunnerReap::test_reap_reports_nothing_reaped` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_process.py::TestProcessRunnerReap::test_reap_json_mode_emits_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_process.py::TestProcessRunnerReap::test_unknown_process_subcommand_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_pytest_spawn_env_wiring.py::TestMutateRunnerWiring::test_must_fire_applies_and_warns_before_run_mutations` (pytest node id, verified passing when recorded)
- `tests/unit/test_pytest_spawn_env_wiring.py::TestPerfRunnerProfileWiring::test_must_fire_applies_and_warns_for_tests_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_pytest_spawn_env_wiring.py::TestPerfRunnerProfileWiring::test_must_stay_quiet_raw_argv_path_does_not_wire` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 74 error(s), 3940 warning(s), 883 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, COV007@src/frob/tickets/_done_report.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DOC011@docs/guides/release.md, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/doctor.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3257, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py
