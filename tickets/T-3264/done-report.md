## Done report

Root cause: `src/frob/gates/_vmodel.py::_collect_vmodel_graph` had an
unguarded `import strata_core` -- called from `vmodel_gate` for ANY repo
with at least one `.strata` file under its design dir, regardless of
whether that file declares any `vmodel_node`/`vmodel_edge` statements
(the "nothing vmodel-shaped, skip" check runs AFTER this call, on its
return value). With `strata_core` genuinely absent (standalone
`uv tool install frob`, T-0134), this raised a bare `ImportError` that
propagated all the way to `frob.__main__.main`'s dispatch loop and
crashed the whole `frob check` run -- even though `sys_gate`'s SYS004
had already run first, correctly degraded via `frob.strata._parse
.parse_module`'s existing guarded import, and logged its own typed
finding for the exact same file. `frob.strata`'s own two guarded
imports (`_parse.py`, `_facts.py`) were never the problem; this was a
separate, unguarded import in a different module entirely
(`frob.gates._vmodel`, not `frob.strata`).

Fix: wrapped the `import strata_core` in `_collect_vmodel_graph` in
`try/except ImportError`, degrading to an empty graph (`vmodel_gate`
then hits its existing "no vmodel declarations" skip and returns no
violations) with a WARNING log line, matching this same module's own
stated posture for a per-file parse failure ("SYS004 already reports
this, duplicating here would double-report"). No change to
`frob.strata` itself was needed -- its guarded-import pattern was
already correct; scope was narrowed off `src/frob/strata/**` for this
reason (`frob ticket scope T-3264 --remove ... --add
src/frob/gates/_vmodel.py`).

Changed:
- src/frob/gates/_vmodel.py::_collect_vmodel_graph (guarded import,
  frob:ticket/frob:tests directives added)

Evidence:
- tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_fails_loud_with_sys004_when_strata_present
  (the ticket's target test, now green: exits nonzero, reports SYS004,
  no crash)
- tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files
  (T-0135 opt-in posture unaffected)
- tests/test_gates_vmodel.py::TestVmodelGate::test_noop_no_vmodel_declarations
  (confirms the pre-existing "design dir present, no vmodel
  declarations" skip path this fix reuses)

All 3 tests in TestNativeMissingFailsLoud and all tests in
tests/test_gates_vmodel.py pass (natives built fresh in this worktree
via `frob natives build`, T-2409-class worktree-natives gap -- this
worktree had none). One unrelated pre-existing failure was observed in
the same natives-build verification pass, OUTSIDE this ticket's scope:
tests/unit/strata/test_vmodel_authoring.py::TestVmodelAuthoringFormat::test_vmodel_node_and_edge_round_trip_through_python
(an `attrs: {}` field now present in parsed vmodel_edge JSON that the
test's exact-equality assertion does not expect -- a kernel/authoring
format drift unrelated to the native-missing degrade path this ticket
fixes; not touched, not filed as a new ticket here since it needs its
own root-cause read this ticket's scope does not cover, but noting it
for whoever next touches that file).

Filed: none.

Gates: `frob check --ticket T-3264 --only scope --only prework` --
gate:SCOPE clean (0 errors, 34 pre-existing warnings unrelated to
touched files). gate:DRIFT/gate:WAIVE FAIL but are REPO-WIDE (not
ticket-scoped) per the tool's own NOTE, and every finding cited is in
files this ticket never touched (src/frob/app/*, src/frob/gates
/_coverage_sites.py, src/frob/gates/_docstatus.py, src/frob/gates
/_waive.py, src/frob/process/parsers/common.py, src/frob/serve
/_events.py, src/frob/tickets/_leases.py, src/frob/tickets
/_worktree_sweep.py, plus unrelated test files) -- pre-existing,
matching the same pattern T-3249/T-3263 already documented for this
repo state.

### Changed
```
 tickets/T-3264/ticket.md | 21 ++++++++++++++++++++-
 1 file changed, 20 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_fails_loud_with_sys004_when_strata_present` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files` (pytest node id, verified passing when recorded)
- `tests/test_gates_vmodel.py::TestVmodelGate::test_noop_no_vmodel_declarations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 78 error(s), 3950 warning(s), 884 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-3262/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DOCENUM001@docs/modules/gates.md, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
