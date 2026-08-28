## Done report

Investigated whether T-3061 (landed at 7862fb4013cd6aaa2af121c6e9754fadfe9000ce,
"Put the 2.9s lint gate back on the rapid land path without re-enabling TEST016
mutation testing") already resolves the incident this ticket was filed for.

The incident: [profile] override_ratchet = true (T-1681) turns off the T-1514
pre-commit sweep on the land path in every profile, so nothing ran `ruff check`
before a commit was published to main; two lint classes (E501, an import-sort/
I001 error) reached main this way on 2026-08-26 and forced a CI abort.

T-3061 added _assert_touched_files_lint_clean_pre_land, wired into
_land_core_prepare unconditionally for EVERY profile including rapid (same
"not relaxed by rapid" posture _assert_touched_files_type_check_pre_land
already established for ty). It runs `ruff check` (this repo's
[tool.ruff.lint] select = ["E", "F", "W", "I"], so E501 and I001 are both
in scope) against exactly the ticket's own touched .py files and refuses
the land (sys.exit(1) before any merge/commit to main) on any violation.
T-3061's own done report includes a real, non-dry-run demonstration: a
planted E402/F401 violation refused a real `frob ticket land` before main
advanced (wall clock ~31.8s). CI run 33035660969 (after T-3061 landed)
shows Lint and Typecheck PASSING on ubuntu, macOS and Windows -- live
confirmation the gate is holding.

This directly closes the exact failure mode T-3060 was filed for: the two
cited lint classes can no longer reach main through override_ratchet,
because T-3061's gate is unconditional across every profile, not merely
restored under override_ratchet=false.

What T-3061 does NOT cover, and is NOT part of closing this incident:
override_ratchet still disables the WIDER pre-commit sweep (all of frob's
own non-ruff gates: ARCH, COV, DUP, SEC, PII, etc.) and TEST016 mutation
testing -- those remain deferred to the post-land sweep under rapid. That
is a distinct, already-tracked, deliberate tradeoff (T-1575's own text:
"single post-land sweep with revert-on-red, no pre-commit sweep"), not a
new incident this ticket was filed to describe, and reintroducing it would
reintroduce the multi-minute land cost override_ratchet exists to avoid --
the owner's explicit "does not halt development too badly" constraint.
Filed T-3083 to track the narrower, still-open gap this investigation
surfaced: `ruff format` (formatting drift, distinct from `ruff check`
lint/import-sort) still has no pre-commit gate at all under rapid, and is
exactly the kind of small, deterministic, auto-fixable class this ticket's
brief called out as fixed-and-continue material -- not invented scope on
this ticket, a real residual gap worth its own small ticket.

No code change needed on T-3060 itself; closing as resolved by T-3061.

### Changed
```
 tickets/T-3060/done-report.md      | 61 ++++++++++++++++++++++++++++++++++++++
 tickets/T-3060/ticket.md           | 12 ++++++--
 tickets/T-3083/ticket.md | 29 ++++++++++++++++++
 3 files changed, 99 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_a_lint_error_in_a_touched_file_refuses_the_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_a_clean_touched_file_does_not_refuse` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 65 error(s), 643 warning(s), 863 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3069/ticket.md, DOC006@tickets/T-3080/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py
