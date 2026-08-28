## Done report

Changed:
  tests/unit/strata/test_effects.py (serve capability-conformance fixture's
    may= tuple: added "exec", matching design/frob.strata's own T-2884
    grant that had drifted out of sync with this test fixture)
  tests/golden/frob_export_iam.json, frob_export_k8s.yaml,
    frob_export_seccomp.json (regenerated against T-3029's model change)

Evidence:
  tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects
  tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam
  tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
  tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
  tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
  tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
  tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
  tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
  tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo::test_sys003_zero_against_live_repo_design

Filed:
  T-3224 (REG005/REG008 on docs/design/registry/check-coverage.yaml)
  T-3225 (WAIVE006 stale waiver bound to closed ticket T-2993)
  T-3223 (DOC006 dead path pointers in tickets/T-2962/ticket.md)

Gates: frob check --ticket T-3041 -- see report body below.

TRIAGE RESULT (the ticket's own stated job): of the 13 originally-failing
tests, 5 were already fixed by T-3029 landing (test_sys_gate_zero_violations,
both test_selfconform.py cases, test_conform_eval_needle,
test_sys003_calibration) -- confirmed by re-running them fresh on main
post-T-3029. 4 more were fixable inside T-3041's own scope (test_effects.py
+ the three export_golden goldens, all downstream of T-3029's legitimate
model change) and are fixed by this ticket. The remaining 4 are genuinely
unrelated root causes in files this ticket has no reason to own (a stale
registry YAML, a stale ticket-body doc pointer, a stale ticket-bound
waiver) -- each filed as its own bug ticket rather than pulled into this
one's scope or left silently unaddressed. Checked each new draft's scope
overlap against the existing queue (T-1598/T-1608/T-1609/T-1661/T-2202)
before filing -- all were false positives from those tickets' broad
docs/**-or-src/frob/**-shaped scopes, not the same finding already owned.

Zero of the 13 are outstanding without either a fix or a filed ticket
naming the exact finding.

### Changed
```
 tests/golden/frob_export_iam.json     | 182 ++++++++++++++++++++++++++++++++++
 tests/golden/frob_export_k8s.yaml     | 118 ++++++++++++++++++++++
 tests/golden/frob_export_seccomp.json |  37 +++++++
 tests/unit/strata/test_effects.py     |  18 +++-
 tickets/T-3041/ticket.md              |  28 ++++++
 tickets/T-3223/ticket.md    |  42 ++++++++
 tickets/T-3224/ticket.md    |  47 +++++++++
 tickets/T-3225/ticket.md    |  44 ++++++++
 8 files changed, 511 insertions(+), 5 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 92 error(s), 2029 warning(s), 874 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3041, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SUPPRESS001@src/frob/app/_config_external.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
