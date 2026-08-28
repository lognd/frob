## Done report

Changed:
- src/frob/app/ticket_runner/_land_cmd.py::_ruff_check_files
- src/frob/app/ticket_runner/_land_cmd.py::_assert_touched_files_lint_clean_pre_land
- src/frob/app/ticket_runner/_land_cmd.py::_land_core_prepare (wired the new call)
- docs/modules/tickets-landing.md (new "Pre-land lint gate (T-3061)" section)
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand

Evidence:
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_a_lint_error_in_a_touched_file_refuses_the_land
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_a_clean_touched_file_does_not_refuse
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_empty_touched_set_is_a_no_op

Real-invocation demonstration (not just unit tests): planted a genuine
import-os unused-import lint error in an in-scope touched file
(src/frob/process/parsers/ruff.py) and ran a real, non-dry-run
frob ticket land T-3061. It refused before merging to main, printing
the exact rule codes and line: ruff check found 2 violations at
ruff.py:111, E402 Module level import not at top of file and F401
os imported but unused. Wall clock for that refusing land: ~31.8s.
git log main confirmed main did NOT advance -- the refusal happens
before the merge/commit-to-main step. The planted error was then
reverted; this land (with the gate's own code intact, clean) is the
clean-land half of the demonstration.

Filed: none

Gates: frob check --only lint clean on the ticket's own touched files
(two pre-existing unrelated ruff-check errors in _rapid_sweep.py and
54 pre-existing ruff-format warnings across the repo are untouched,
out of this ticket's scope).

### Changed
```
 docs/modules/tickets-landing.md           |  30 ++++++++
 src/frob/app/ticket_runner/_land_cmd.py   | 116 +++++++++++++++++++++++++++++-
 tests/test_ticket_work_and_land_finish.py |  52 ++++++++++++++
 tickets/T-3061/ticket.md                  |  38 +++++++++-
 4 files changed, 234 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_a_lint_error_in_a_touched_file_refuses_the_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_a_clean_touched_file_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_empty_touched_set_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 64 error(s), 942 warning(s), 857 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/entity_architecture.md, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3063/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOCENUM001@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, E501@/home/logan/projects/frob/.claude/worktrees/t-3061-series/src/frob/app/ticket_runner/_rapid_sweep.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3061-series/src/frob/app/ticket_runner/_rapid_sweep.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3061, REF001@docs/strata/entity_architecture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@tests/unit/strata/entity_arch/storage_cheap.strata, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py
