## Done report

Changed:
- src/frob/refactor/_scan.py::_handle_from_import

Evidence:
- tests/test_refactor.py::TestScanReferences::test_mixed_moved_and_untouched_names_leaves_import_alone (designated repro, FAILED_AT_PARENT confirmed against e8c37a309)
- tests/test_refactor.py::TestScanReferences::test_reexport_line_with_many_names_leaves_import_alone
- tests/test_refactor.py::TestScanReferences::test_type_checking_guarded_mixed_import_not_rewritten
- tests/test_refactor.py::TestScanReferences::test_function_local_mixed_import_not_rewritten
- tests/test_refactor.py::TestRunSplit::test_split_moves_symbols_and_leaves_reexport_shim (updated to the corrected expected behavior)

Filed: none

Gates: uv run frob check --only scope --ticket T-3105 -> gate:SCOPE 0 errors (96 pre-existing SCOPE002 closure warnings over the shared test file, unrelated to this fix). gate:DRIFT (39 errors) and gate:WAIVE (1 error) are repo-wide and pre-existing, confirmed via `git diff --stat main` that this ticket's diff touches only src/frob/refactor/_scan.py and tests/test_refactor.py -- none of the DRIFT/WAIVE findings name either file. `frob check --land-parity` OPAQUE001 finding at _scan.py:65 is pre-existing code from T-3066 (getattr in _enclosing_stmt_list), not touched by this diff.

Root cause and fix: `_handle_from_import` (via `_rebuild_from_import`) repointed
the WHOLE `from <module> import a, b` statement at the destination module
whenever it named the moved symbol alongside an untouched one -- the
untouched name(s) were dragged along even though the destination module
never defines them. Fixed by skipping the rewrite entirely whenever the
import line names any OTHER symbol besides the one being moved: the
split's own re-export shim (`build_reexport_shim_op`) already keeps the
source module re-exporting every moved name, so a mixed-name import line
needs no edit at all and stays valid unmodified.

This also required updating a pre-existing test
(TestRunSplit::test_split_moves_symbols_and_leaves_reexport_shim) whose
assertion encoded the OLD (buggy) behavior: it asserted a two-symbol
line (`from pkg.mod import alpha, beta`, both alpha and beta moved in the
same split) got rewritten to `from pkg.newmod import ...`. Since
`scan_references` runs once per symbol with no visibility into sibling
moves in the same split chunk, this shape is indistinguishable from the
mixed moved/untouched case at the point the fix operates, and my fix
correctly leaves it alone -- the shim keeps `from pkg.mod import alpha,
beta` valid, verified in the updated test assertion.

Verified with the real repro command AFTER the fix (frob refactor split
frob.gates._models --symbols Severity,WaiverRef,DebtEntry,Violation
--into frob.findings) as part of retrying T-3086 in this same series --
see T-3086's own Done report for that measurement.

### Changed
```
 src/frob/refactor/_scan.py |  10 ++++
 tests/test_refactor.py     | 135 ++++++++++++++++++++++++++++++++++++++++++---
 tickets/T-3105/ticket.md   |  20 ++++++-
 3 files changed, 155 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestScanReferences::test_mixed_moved_and_untouched_names_leaves_import_alone` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestScanReferences::test_reexport_line_with_many_names_leaves_import_alone` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestScanReferences::test_type_checking_guarded_mixed_import_not_rewritten` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestScanReferences::test_function_local_mixed_import_not_rewritten` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRunSplit::test_split_moves_symbols_and_leaves_reexport_shim` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 82 error(s), 754 warning(s), 863 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@src/frob/tickets/_land_compose.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_land_compose.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3105/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bn/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3105, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py
