## Done report

Changed:
  tests/system/test_cli_ticket.py (3 fixtures: --scope added)
  tests/system/test_cli_ticket_promote.py (--scope added)
  tests/test_ticket_leases.py::TestCommitFullLedgerChange.test_archive_cli_leaves_repo_clean (ticket_scope added)
  tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome (monkeypatch typo fixed)
  tests/test_ticket_evidence.py::TestEvidenceCmdCwd.test_relative_probe_only_succeeds_from_worktree (silent probe swapped for grep -c)
  tests/system/test_cli_ticket_land.py::TestLandCLI.test_dry_run_reports_clean (T-2114/COV001 directives added to fixture)

Reduced count after T-3081 landed first (as the coordinator asked to
verify): re-ran all 10 of T-3080's originally-listed node ids against
main AFTER T-3081's fix landed. 9 of 10 still failed with the exact
"EMPTY scope" refusal; the 10th (test_start_auto_plans_queued_ticket)
now passed -- but NOT because of T-3081's fix. It was independently
fixed by a concurrent sibling land (T-3087, commit 187ca0de8) that
happened to add --scope pkg.py to that same fixture while working an
unrelated blocked_by/close bug. T-3081's own fix (the no_scope_declared
round-trip) does not reduce this count on its own: none of these 10
tests ever call TicketSpec/`frob ticket new --no-scope` directly -- they
simply never declare a scope at all, which is a different code path
(T-2394's "declared vs omitted" distinction) than the one T-3081 fixed.

Test-vs-product for each defect:
  - 8 of the 10 (all of test_cli_ticket.py/test_cli_ticket_promote.py/
    test_ticket_leases.py's node ids): TEST-side, exactly T-3037's own
    empty-scope fixture-drift class -- the ticket-minting helper never
    declared a scope. Fixed by adding --scope/ticket_scope to the exact
    file each fixture already creates.
  - test_ticket_land_proof_claims.py (3 node ids, one ticket-brief entry):
    TEST-side, but a DIFFERENT and unrelated bug: the file's own
    `_land_proof_checks` monkeypatch has carried `state_ok=False` since
    its T-2091 origin commit (confirmed via `git log -p`), which makes
    `verified = ancestor_ok and state_ok` structurally False regardless
    of the claims-reverify outcome under test -- the "healthy path"
    assertions (`verified is True`) were unreachable from day one. This
    is NOT the T-2394 empty-scope class the ticket described; corrected
    the monkeypatch value to `True` (a genuinely healthy ancestor+state
    pair, matching what each test's docstring already says it means).
  - test_ticket_evidence.py::test_relative_probe_only_succeeds_from_
    worktree: TEST-side, also unrelated to T-2394: a LATER guard
    (T-1892's EvidenceCmdSilent) now refuses an exit-0 command with no
    stdout/stderr, which broke this test's `test -f marker.txt` probe
    on its "right cwd" half. Swapped for `grep -c present marker.txt`,
    which emits output and still exercises the same cwd-honoring
    behavior.

ALSO IN SCOPE (per the brief): tests/system/test_cli_ticket_land.py::
TestLandCLI::test_dry_run_reports_clean, which the brief said "fails at
a DIFFERENT, later guard ... needs its own look." Re-checked: fails at
T-2114 (new-public-symbol doc/test-edge check) on the fixture's own
synthetic `new_thing()` def, unrelated to T-2394. Fixed by adding the
frob:tests directive T-2114 requires plus a frob:waive COV001 for the
frob:doc half (a throwaway fixture symbol, not a real documented API).

Filed: T-3098 (renumbers at land) -- found while re-running
this ticket's own touched-set tests: T-3087's land added a `reopen` verb
to the ticket dispatch table but never added it to
TestLedgerAutoCommitEnumeratedOverDispatchTable's exhaustiveness buckets
in tests/test_ticket_leases.py, so
test_dispatch_table_verbs_are_all_accounted_for now fails. Confirmed
pre-existing (reproduces on main before any of this ticket's edits),
unrelated to T-3080's own scope/diff -- filed rather than fixed silently.

Gates: frob check --ticket T-3080 (--only scope/prework/fmt/affect_drift)
clean (0 errors) after narrowing scope to include the filed draft's own
ticket dir (tickets/T-3098/**). Repo-wide gate families (DRIFT/
PRE/WAIVE, not scoped to this ticket per the tool's own scope-note) show
pre-existing failures unrelated to this diff.

### Changed
```
 tests/system/test_cli_ticket.py         |  6 +++++
 tests/system/test_cli_ticket_land.py    |  7 ++++++
 tests/system/test_cli_ticket_promote.py |  2 ++
 tests/test_ticket_evidence.py           | 17 ++++++++++---
 tests/test_ticket_land_proof_claims.py  | 19 +++++++++++---
 tests/test_ticket_leases.py             |  1 +
 tickets/T-3080/ticket.md                | 38 ++++++++++++++++++++++++++--
 tickets/T-3098/ticket.md      | 44 +++++++++++++++++++++++++++++++++
 8 files changed, 124 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_skipped_unmeasured_is_not_printed_as_verified_true` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_passed_healthy_path_is_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_no_recorded_outcome_leaves_verified_unaffected` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestEvidenceCmdCwd::test_relative_probe_only_succeeds_from_worktree` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promotes_a_draft_carrying_evidence_and_done_report` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_start_auto_plans_queued_ticket` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_without_evidence_fails` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_with_evidence_and_done_report_succeeds` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_plan_then_sweep_flow` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_archive_cli_leaves_repo_clean` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 76 error(s), 785 warning(s), 862 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3080/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3088/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bh/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3080, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py
