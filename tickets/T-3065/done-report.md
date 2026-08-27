## Done report

T-3065's own quarantine finding identity fix, plus the fresh field
evidence folded into the ticket body (2026-08-26/27, items a/b/c).

Evidence:
- tests/unit/verify/test_verify_runner.py::TestDispose::test_dismiss_with_relative_path_matches_a_finding_stored_absolute
  (BUG002: confirmed FAILING at the parent commit before the fix, per
  the playbook's test-first requirement)
- tests/unit/verify/test_quarantine.py::TestNormalizeFindingPath::test_absolute_and_relative_resolve_identical
- tests/unit/verify/test_quarantine.py::TestNormalizeFindingPath::test_empty_file_passes_through
- tests/unit/verify/test_quarantine.py::TestNormalizeFindingPath::test_unresolvable_path_falls_back_verbatim
- tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_normalizes_an_absolute_file_to_root_relative_at_write_time
- tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_an_already_relative_file_is_left_as_is
  (must-fire / must-stay-quiet pair)
- `frob test --base main`: python exit=0, 26 outcomes recorded, clean

Field evidence disposition:
- (a) absolute-vs-relative dismiss mismatch: FIXED by this change (the
  regression test above reproduces it exactly at the parent commit).
- (b) line=None finding unaddressable: INVESTIGATED, not a separate
  grammar gap -- `_parse_finding_arg` already leaves `line=None` for a
  2-part `RULE:FILE` key. Recorded in the ticket body as a known
  residual limitation of the (rule_id, file, line) identity shape (two
  None-line findings on the same file/rule would collide); not fixed
  here since no such collision was actually observed.
- (c) stale quarantine.json surviving a clear: INVESTIGATED, NOT fixed
  here -- `clear_quarantine`'s "keep the cleared record, never delete"
  contract is itself covered by many existing tests in
  tests/unit/test_rapid_sweep.py and
  tests/unit/verify/test_verify_runner.py (asserting load_quarantine
  returns the cleared record with cleared_at/cleared_reason/cleared_by
  populated). Making the file's bare on-disk existence truthful is a
  real, larger fix that would need to touch that whole tested surface,
  not a small addition to this bugfix.

Filed: T-3082 ("quarantine.json persists on disk after clear;
a stale cleared record is byte-identical in shape to a live one") --
gets a real ticket id at land/renumber time.

Gates: `frob check --ticket T-3065 --only affect_drift --only fmt
--only scope --only prework --only coverage` clean for this ticket's
touched files (gate:AFFECT 0, gate:FMT 0, gate:SCOPE 0, gate:PRE 0,
gate:COV 0 for src/frob/verify/_quarantine.py and
src/frob/app/verify_runner.py -- remaining gate:COV/DRIFT/DSL/WAIVE
errors are pre-existing, repo-wide, and untouched by this ticket's
diff, per gate:scope-note).

### Changed
```
 frob.lock                               | 66 ++++++++++++++++++++++++++++++++-
 src/frob/app/verify_runner.py           | 31 ++++++++++++----
 src/frob/verify/_quarantine.py          | 58 +++++++++++++++++++++++++++++
 tests/unit/verify/test_quarantine.py    | 64 ++++++++++++++++++++++++++++++++
 tests/unit/verify/test_verify_runner.py | 42 +++++++++++++++++++++
 tickets/T-3065/ticket.md                | 20 +++++++++-
 tickets/T-3082/ticket.md      | 65 ++++++++++++++++++++++++++++++++
 7 files changed, 336 insertions(+), 10 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 76 error(s), 676 warning(s), 864 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3066/ticket.md, DOC006@tickets/T-3069/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3065/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/ticket_runner/_new.py, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@src/frob/app/_config_external.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
