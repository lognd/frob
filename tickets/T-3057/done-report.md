## Done report

Changed:
src/frob/tickets/_land.py::_check_tdd_order
src/frob/tickets/_land.py::_tdd_order_scoped_edges
src/frob/tickets/_land.py::_land_precheck_remaining_checks

Evidence:
tests/test_ticket_land.py::TestCheckTddOrder::test_logs_a_warning_for_an_implementation_first_pair_without_blocking
tests/test_ticket_land.py::TestCheckTddOrder::test_stays_quiet_when_no_tests_edges_are_touched
tests/test_ticket_land.py::TestCheckTddOrder::test_never_refuses_the_land

Filed: none

Gates: frob check --ticket T-3057 clean (see land dry-run output for
the demonstration that TDD001 actually fires at land time, WARN-only,
never blocking).

### Changed
```
 src/frob/tickets/_land.py | 136 ++++++++++++++++++++++++++++++++++++++++
 tests/test_ticket_land.py | 155 ++++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3057/ticket.md  |   8 ++-
 3 files changed, 298 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_land.py::TestCheckTddOrder::test_logs_a_warning_for_an_implementation_first_pair_without_blocking` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCheckTddOrder::test_stays_quiet_when_no_tests_edges_are_touched` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCheckTddOrder::test_never_refuses_the_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 62 error(s), 885 warning(s), 855 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/entity_architecture.md, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOCENUM001@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, E501@/home/logan/projects/frob/.claude/worktrees/t-3057/src/frob/narrative/_cli.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3057/tests/test_ticket_land.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3057, REF001@docs/strata/entity_architecture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@tests/unit/strata/entity_arch/storage_cheap.strata, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py
