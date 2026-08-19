## Done report

Changed:
- src/frob/app/ticket_runner/__init__.py::__all__ (added `_LEDGER_TRANSACTIONAL_VERBS`)

Evidence:
- tests/unit/test_ticket_runner_ledger_verbs_export_t2647.py::TestLedgerTransactionalVerbsExportIsDeclared.test_ticket_runner_init_has_no_f401_finding (designated repro; FAILED_AT_PARENT verified against commit 07efdd760, base-ref of the test-only commit before the __all__ fix)
- tests/unit/test_ticket_runner_ledger_verbs_export_t2647.py::TestLedgerTransactionalVerbsExportIsDeclared.test_ledger_transactional_verbs_still_importable_from_ticket_runner (positive control: the real external consumer -- tests/test_ticket_leases.py -- still resolves the name)

Filed: none -- no out-of-scope work found. (The pre-existing dispatch-table verb-accounting failure in
tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for
fails identically before and after this change -- unrelated to the F401 fix, not attributed here, not
re-filed since it is presumably already covered by the known T-2630..T-2637 red-test set or a pre-existing
gap in that test's own verb bookkeeping.)

Gates: `uv run frob check --only test --ticket T-2647` shows 1 error (TEST001 on
src/frob/strata/_multifile.py::SealedGrantSet.from_root_node) and 3 DRIFT001 errors
(src/frob/_cli_parsers/_ticket/_new.py::_add_ticket_new_parser,
src/frob/app/ticket_runner/_verify.py::_parse_error_findings_from_json,
src/frob/tickets/__init__.py::_doable_sort_key) -- all pre-existing, none touching this
ticket's scope or any file this ticket edited; not attributed to T-2647.
`ruff check --select F401 src/frob/app/ticket_runner/__init__.py` -> All checks passed!

### Changed
```
 src/frob/app/ticket_runner/__init__.py             |  7 ++-
 ...test_ticket_runner_ledger_verbs_export_t2647.py | 62 ++++++++++++++++++++++
 tickets/T-2647/ticket.md                           | 21 +++++++-
 3 files changed, 87 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_ledger_verbs_export_t2647.py::TestLedgerTransactionalVerbsExportIsDeclared::test_ticket_runner_init_has_no_f401_finding` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_verbs_export_t2647.py::TestLedgerTransactionalVerbsExportIsDeclared::test_ledger_transactional_verbs_still_importable_from_ticket_runner` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2647, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
