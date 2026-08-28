## Done report

Fixed the indentation-loss corruption in `frob refactor split`'s
call-site import rewrite: `_import_op` now prefixes the replacement
`from ... import ...` statement with `" " * node.col_offset` before
building the `RewriteOp`, so an indented (function-local or block-nested)
`from`-import call site keeps its original leading whitespace instead of
orphaning the following, still-indented sibling line at "unexpected
indent".

Evidence:
- tests/test_refactor.py::TestScanReferences::test_function_local_import_rewrite_preserves_indentation
- tests/test_refactor.py::TestApplyPlan::test_apply_indented_import_call_site_stays_parseable

Both were confirmed to FAIL against the parent commit (reverted the fix
locally, reran, confirmed the exact unindented-`new_text` failure; then
reapplied the fix and confirmed both pass) per BUG002 test-first.

Filed: none -- no out-of-scope work discovered.

Gates: `frob check --ticket T-3109` clean (0 scoped errors against
src/frob/refactor/_scan.py or tests/test_refactor.py) after building the
missing native extensions (frob_core/strata_core) in this worktree via
`uv run frob natives build` -- their absence had been producing unrelated
ty/collection errors, not caused by this change. A full-suite
`frob test --base main` surfaces pre-existing failures reproduced
identically on the primary checkout outside this worktree (e.g.
tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged),
unrelated to this fix.

### Changed
```
 src/frob/refactor/_scan.py | 12 +++++++--
 tests/test_refactor.py     | 62 ++++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3109/ticket.md   | 13 +++++++++-
 3 files changed, 84 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestScanReferences::test_function_local_import_rewrite_preserves_indentation` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestApplyPlan::test_apply_indented_import_call_site_stays_parseable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 93 error(s), 762 warning(s), 864 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3110/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bp/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/ticket_runner/_new.py, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@src/frob/app/_config_external.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
