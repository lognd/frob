## Done report

Changed:
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable._MUTATING_VERB_INVOCATIONS
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable._READ_ONLY_VERBS
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable._NEEDS_DEDICATED_FIXTURE
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable.test_verb_leaves_repo_clean

Root cause: TEST fixture drift, not a product defect. Confirmed by reading
src/frob/app/ticket_runner/_mutate.py: _priority/_kind/_component/_tier all
correctly call _resolve_triage_reason and refuse without --reason (a real,
intentional guard, T-2353/T-2394-adjacent). The shared dispatch-table
fixture in tests/test_ticket_leases.py predates that guard and never passed
--reason for those four verbs. While confirming test_dispatch_table_verbs_
are_all_accounted_for, found the SAME fixture had also drifted against
7 newer verbs (contention, unblock, waive-audit, body, set-parent,
runs-last-parallel-safe, milestone) added to the dispatch table since the
fixture was last updated -- same root-cause class, same file, so folded
into this one fixture fix rather than filing separately.

Evidence: (bound via frob ticket evidence)
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[component]
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[kind]
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[priority]
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[tier]

All 17 tests in TestLedgerAutoCommitEnumeratedOverDispatchTable pass; full
tests/test_ticket_leases.py file passes except
TestCommitFullLedgerChange::test_archive_cli_leaves_repo_clean, which is
the SAME T-2394 empty-scope guard hitting a DIFFERENT stale fixture and is
already covered by T-3037's scope -- confirmed still failing at HEAD
before touching it, left untouched here.

Filed: none (T-3037 already covers the one adjacent failure noticed).
Gates: frob check --ticket T-3035 clean of new findings; pre-existing
ruff-format/frob-cycle/graph-build findings are repo-wide and absorbed by
`frob ticket land`'s own fmt pass, not introduced by this change.

### Changed
```
 tests/test_ticket_leases.py | 65 ++++++++++++++++++++++++++++++++++++++++++---
 tickets/T-3035/ticket.md    |  6 +++++
 2 files changed, 67 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[component]` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[kind]` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[priority]` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[tier]` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 61 error(s), 749 warning(s), 862 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3066/ticket.md, DOC006@tickets/T-3069/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOCENUM001@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py
