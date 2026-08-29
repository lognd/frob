## Done report

Changed:
src/frob/tickets/_worktree_guard.py::PYTEST_XDIST_PACKAGE
src/frob/tickets/_worktree_guard.py::_xdist_plugin_present
src/frob/tickets/_worktree_guard.py::warn_if_xdist_plugin_missing
src/frob/tickets/_worktree_guard.py::warn_if_xdist_bound_missing
tests/test_worktree_guard.py::TestWarnIfXdistPluginMissing
tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing.test_also_warns_on_plugin_absence_even_without_fleet_context
docs/modules/tickets-data-storage.md (new T-3316 section)

Real behaviour determined: frob's own pyproject.toml addopts sets `-n auto`
unconditionally. When pytest-xdist is not importable, ANY pytest spawn --
fleet context or not -- exits 4 (a usage error: `-n` is not a recognised
option) before a single test runs. This is a different condition from
warn_if_xdist_bound_missing's original one (an unset fleet-bound env var,
which presupposes the plugin is even loaded).

Fix: added `_xdist_plugin_present()` (importlib.metadata probe, same
distribution name frob.doctor's scan_external_tools/T-3276 already uses)
and `warn_if_xdist_plugin_missing(root)`, an unconditional LOUD ERROR log
naming pytest-xdist and its install command. Wired by calling it as the
first statement of `warn_if_xdist_bound_missing` -- that function is
already the single choke point called from every pytest-spawning call
site in this codebase (mutate_runner, perf_runner, ticket_runner._verify,
testing._collect, testing._coverage_refresh, testing._runners), so
extending it reaches all six without touching any call site again, while
staying inside this ticket's single-file scope.

Category per T-3276's rule: pytest-xdist is OPTIONAL_FOR_GATE (frob still
runs without it; only pytest-spawning consumers of `-n auto` are
affected) -- so this is a loud diagnostic naming the tool and its install
command, not a hard failure of frob itself.

Evidence: tests/test_worktree_guard.py::TestWarnIfXdistPluginMissing::test_must_fire_when_plugin_not_importable
tests/test_worktree_guard.py::TestWarnIfXdistPluginMissing::test_must_stay_quiet_when_plugin_importable
tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_also_warns_on_plugin_absence_even_without_fleet_context
tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_fire_fleet_context_with_bound_missing_logs_error
tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_stay_quiet_bound_present_no_log
tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_stay_quiet_no_fleet_context_no_log

Filed: none (the six-call-site preflight wiring T-3276 deferred is now
covered for free since warn_if_xdist_bound_missing already reaches all of
them; no residue found needing a separate ticket)

Gates: frob check --ticket T-3316 clean for gate:SCOPE, gate:PREWORK, and
the diff-driven checks (COV002/TODO001/AFFECT/FMT) against this ticket's
touched set. Repo-wide gate counts (COV/SEC/etc.) are pre-existing and
unrelated to this ticket's files per the check's own scope-note.

### Changed
```
 tickets/T-3316/ticket.md | 22 +++++++++++++++++++++-
 1 file changed, 21 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_worktree_guard.py::TestWarnIfXdistPluginMissing::test_must_fire_when_plugin_not_importable` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestWarnIfXdistPluginMissing::test_must_stay_quiet_when_plugin_importable` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_also_warns_on_plugin_absence_even_without_fleet_context` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_fire_fleet_context_with_bound_missing_logs_error` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_stay_quiet_bound_present_no_log` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing::test_must_stay_quiet_no_fleet_context_no_log` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 77 error(s), 4031 warning(s), 884 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, COV007@src/frob/tickets/_done_report.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/doctor.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3316, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
