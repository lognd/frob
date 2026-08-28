## Done report

MEASURED VERDICT: real product regression in D-02, not test staleness.

Root cause: T-1944 (commit 49abc109e, landed 2026-08-10) made
`_append_evidence_and_write` (src/frob/tickets/_evidence.py)
unconditionally auto-add EVERY newly-cited evidence node id's own file
into `ticket.evidence_scope`, regardless of any real relationship to the
ticket's declared work. `evidence_covers_scope` (D-02,
src/frob/gates/__init__.py) treats `evidence_scope` exactly like `scope`
for self-cover purposes -- so from the moment T-1944 landed, EVERY
`add_evidence` call made its own cited node id satisfy D-02 by
definition, the instant it was cited. Confirmed by direct reproduction
(scoped ticket to `src_a/`, evidence bound to a provably unrelated
`tests/test_unrelated.py::test_it` with zero TESTS graph edge, non-empty
declared scope) and by T-1944's own test suite
(`test_evidence_covers_scope_true_via_evidence_scope_alone`), which
explicitly asserted the exact same tautological shape as correct.

Fix: removed the automatic widening from `_append_evidence_and_write`.
`evidence_scope` now only grows via the pre-existing, deliberate
`demote_to_evidence_only` (requires an explicit `--reason`), which
remains the correct, intentional remedy for T-1944's real motivating
incident (T-1686: an epic citing a genuinely-covering pre-existing test,
wrongly forced into `scope` and thus leasing the whole file). Updated
T-1944's own test suite (tests/unit/test_tickets_evidence_only_scope.py)
to exercise `evidence_scope` via the deliberate demote path instead of
asserting the auto-widen that no longer happens.

Blast radius: every `frob ticket close`/`land` since 2026-08-10 (T-1944,
49abc109e) that recorded evidence NOT already covered by declared
`scope`/a genuine TESTS graph edge had D-02 silently satisfied by
definition -- i.e. D-02 has been a no-op for that population for ~17
days. This lines up with T-3046's repo-wide reach measurement (733
bindings: 95.5% reaching, 1.2% not reaching, 3.3% unknown) as an
INDEPENDENT signal of the same underlying property; the two checks
should now agree going forward since D-02 is restored. A full audit of
closes made 2026-08-10..now to identify which specific ones relied on
the defeated check is out of scope for this ticket (no scope declared
for such an audit here) -- filed as a residue ticket, see below.

Changed:
- frob.tickets._evidence._append_evidence_and_write
- tests/unit/test_tickets_evidence_only_scope.py (TestAddEvidenceAutoPopulatesEvidenceOnlyScope, TestEvidenceOnlyScopeNeverLeases, TestEvidenceCoversScopeWithEvidenceOnlyScope)

Evidence:
- tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd::test_close_fails_on_unrelated_evidence (designated BUG002 repro, FAILED_AT_PARENT confirmed)
- tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd::test_close_fails_on_red_evidence (D-01 sibling, still enforces)
- tests/unit/test_tickets_evidence_only_scope.py::TestAddEvidenceAutoPopulatesEvidenceOnlyScope::test_new_evidence_never_auto_widens_evidence_scope
- tests/unit/test_tickets_evidence_only_scope.py::TestEvidenceOnlyScopeNeverLeases::test_evidence_scope_path_does_not_block_another_tickets_add
- tests/unit/test_tickets_evidence_only_scope.py::TestEvidenceCoversScopeWithEvidenceOnlyScope::test_evidence_covers_scope_true_via_evidence_scope_alone
- tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly::test_demote_releases_the_lease_and_keeps_evidence_covered

Filed: T-3147 (renumbers at land) -- audit closes landed
2026-08-10..2026-08-27 for evidence that relied on the defeated D-02
self-cover route, to find any that should not have closed.

Gates: frob check --ticket T-3141 to be run before close.

### Changed
```
 src/frob/tickets/_evidence.py                  | 47 ++++++++++--------
 tests/unit/test_tickets_evidence_only_scope.py | 68 +++++++++++++++++++++-----
 tickets/T-3141/ticket.md                       | 56 +++++++++++++++++++--
 tickets/T-3147/ticket.md             | 47 ++++++++++++++++++
 4 files changed, 181 insertions(+), 37 deletions(-)
```

### Evidence
- `tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd::test_close_fails_on_unrelated_evidence` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd::test_close_fails_on_red_evidence` (pytest node id, verified passing when recorded)
- `tests/unit/test_tickets_evidence_only_scope.py::TestAddEvidenceAutoPopulatesEvidenceOnlyScope::test_new_evidence_never_auto_widens_evidence_scope` (pytest node id, verified passing when recorded)
- `tests/unit/test_tickets_evidence_only_scope.py::TestEvidenceOnlyScopeNeverLeases::test_evidence_scope_path_does_not_block_another_tickets_add` (pytest node id, verified passing when recorded)
- `tests/unit/test_tickets_evidence_only_scope.py::TestEvidenceCoversScopeWithEvidenceOnlyScope::test_evidence_covers_scope_true_via_evidence_scope_alone` (pytest node id, verified passing when recorded)
- `tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly::test_demote_releases_the_lease_and_keeps_evidence_covered` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 79 error(s), 767 warning(s), 866 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-1944, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3139/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-cb/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
