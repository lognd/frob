## Done report

Changed:
src/frob/refactor/_scan.py::_enclosing_stmt_list
src/frob/refactor/_scan.py::_shares_line_with_sibling_statement
src/frob/refactor/_scan.py::scan_references

Evidence:
tests/test_refactor.py::TestScanReferences::test_function_local_import_does_not_false_refuse
tests/test_refactor.py::TestScanReferences::test_if_block_import_does_not_false_refuse
tests/test_refactor.py::TestScanReferences::test_try_block_import_does_not_false_refuse
tests/test_refactor.py::TestScanReferences::test_untouched_symbol_nested_import_does_not_gate_move
tests/test_refactor.py::TestScanReferences::test_semicolon_joined_from_import_refuses_rewrite (pre-existing must-fire fixture, still passes)

All four new must-stay-quiet fixtures were run against the pre-fix
worktree HEAD (before the fix commit) and confirmed to FAIL (false
"semicolon-joined" refusal), then confirmed to PASS after the fix --
manual before/after run since `--check-repro` cannot retroactively
verify a test bound in the same squash-landed commit as its fix
(docs/modules/tickets.md#check-repro-post-land-limitation-t-2025).

Filed: none

Gates: `frob check --only scope --ticket T-3066` clean (0 errors, 96
warnings -- all pre-existing scope-closure under-capture notices on
symbols/tests this ticket did not touch the definition of). Repo-wide
gate:DRIFT (21 errors) and gate:WAIVE (1 error, T-2993) are pre-existing
and unrelated to this ticket's scope -- not caused by this change, not
waived away.

### Changed
```
 src/frob/refactor/_scan.py |  57 +++++++++++++++++++------
 tests/test_refactor.py     | 101 +++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3066/ticket.md   |  15 ++++++-
 3 files changed, 159 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestScanReferences::test_function_local_import_does_not_false_refuse` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestScanReferences::test_if_block_import_does_not_false_refuse` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestScanReferences::test_try_block_import_does_not_false_refuse` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestScanReferences::test_untouched_symbol_nested_import_does_not_gate_move` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestScanReferences::test_semicolon_joined_from_import_refuses_rewrite` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 63 error(s), 725 warning(s), 863 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3066/ticket.md, DOC006@tickets/T-3069/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOCENUM001@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, OPAQUE001@src/frob/refactor/_scan.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3066, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py
