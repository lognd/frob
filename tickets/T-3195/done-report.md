## Done report

COUNT (as requested, first deliverable): 45 hollow done-reports on main --
git grep -l "(no changed files detected)" -- tickets/ intersected with
grep -l "(no evidence recorded)" over that list, excluding this ticket's
own body (which quotes the pattern, not an instance), then confirmed
every remaining ticket carries state: done. This is a systemic accounting
hole, not a one-off.

WRITE PATH: TicketError.MissingEvidence's own guard
(frob.tickets._evidence._done_transition_structural_guard) already
refuses a DONE transition with empty evidence/no Done report UNLESS
`rapid` profile is active, in which case it only records rapid-debt and
lets the close proceed. That rapid branch was the open door: a ticket
can close in rapid mode carrying a Done report whose Evidence and
Changed sections both rendered their literal empty-case placeholder
text, and nothing refused it.

GUARD BUILT: frob.tickets._done_report (new module, T-3195 scope) adds
`_is_hollow_done_report` (true when a Done report body contains BOTH
"(no evidence recorded)" and "(no changed files detected)") and
`_hollow_done_report_exempt` (true for a DOCS-kind rapid close -- frob
has no separate "chore" kind -- or a narrative explicitly recording a
no-behaviour-change close). Wired into
`_done_transition_structural_guard` in frob.tickets._evidence,
unconditionally (runs even under rapid, closing exactly the gap that let
T-3157's hollow report through), returning the new
`TicketError.HollowDoneReport`.

Existing 45 hollow reports on main are left untouched -- this only
refuses NEW ones going forward.

CORRECTION during this same ticket: the first version of
`_is_hollow_done_report` did a raw substring search over the whole Done
report body, which false-fired on THIS ticket's own done-report (its
narrative quotes the two marker strings while explaining the guard).
Fixed to scope the check to the actual `### Changed`/`### Evidence`
section CONTENT (exact match against the placeholder, via
`_done_report_section_lines`/`_section_body`), never free narrative text
-- a new regression test
(test_narrative_mentioning_the_markers_is_never_flagged) locks this in.

### Changed
```
 tickets/T-3195/done-report.md | 48 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3195/ticket.md      | 47 +++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 94 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets.py::TestHollowDoneReportGuard::test_rapid_hollow_report_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestHollowDoneReportGuard::test_docs_kind_rapid_hollow_report_exempt` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestHollowDoneReportGuard::test_no_behaviour_change_narrative_exempt` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestHollowDoneReportGuard::test_real_evidence_never_flagged_as_hollow` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestHollowDoneReportGuard::test_narrative_mentioning_the_markers_is_never_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 76 error(s), 1017 warning(s), 879 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3195/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3195, REF002@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@src/frob/check/_python.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
