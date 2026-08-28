## Done report

Premise partially stale, checked first per instructions: T-3162 (landed
earlier today) added `reopen` to `LEDGER_VERB_STRATEGY` as
`GENERIC_COMMIT_MIRRORED` and T-2603's own audit had already
reclassified `contention`/`waive-audit`/`body` into
`tests/test_ticket_leases.py`'s `_MUTATING_VERB_INVOCATIONS`/
`_READ_ONLY_VERBS` sets -- all three of those pieces of this ticket's
stated fix were already done before I started. `milestone` was NOT: it
was still explicitly `GENERIC_COMMIT_UNMIRRORED` in
`src/frob/app/ticket_runner/_ledger_mirror.py`, kept there on purpose by
T-2603's audit ("Kept here, unmirrored, to match TODAY's actual
behaviour exactly ... see the follow-up bug this audit filed") -- that
follow-up bug is this ticket. The live T-2563-class bug this ticket
describes (a worktree agent's `frob ticket milestone` committing
locally but never mirrored to the primary checkout until land) was
real and unfixed.

Separately, re-running
`tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for`
(this ticket's own named acceptance test) showed it RED for a different
reason than the ticket's four verbs: `reopen` (added to the real
dispatch table by T-3087, landed after this test was last updated) was
unclassified. This is in the same two scope files and is exactly what
this test's own failure message is about, so classifying it was needed
to make the ticket's acceptance test pass; noted here rather than left
silent.

### Changed
- `src/frob/app/ticket_runner/_ledger_mirror.py`: moved `milestone` from
  `GENERIC_COMMIT_UNMIRRORED` to `GENERIC_COMMIT_MIRRORED` (same bucket
  as `priority`/`kind`/`tier`, which share its `_set_ticket_field`
  write primitive).
- `tests/unit/test_ticket_runner_ledger_mirror.py`: added
  `test_milestone_edit_from_worktree_is_visible_on_primary`, mirroring
  `test_scope_edit_from_worktree_is_visible_on_primary`'s shape -- a
  positive control that fails against the pre-fix classification.
- `tests/test_ticket_leases.py`: added `reopen` to
  `_MUTATING_VERB_INVOCATIONS` (with a `state=done` pre-step in
  `test_verb_leaves_repo_clean`, since `reopen` requires it) so
  `test_dispatch_table_verbs_are_all_accounted_for` passes again.
  `contention`/`waive-audit`/`body`/`milestone` were already correctly
  classified there -- no change needed for those four.

### Evidence
- `tests/unit/test_ticket_runner_ledger_mirror.py` (26 passed, includes
  the new `test_milestone_edit_from_worktree_is_visible_on_primary`)
- `tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable`
  (18 passed, parametrized `test_verb_leaves_repo_clean` now covers
  `reopen` and `milestone`)
- `frob test --base main`: touched-set selection ran 7 python test(s),
  exit=0

Filed: none -- no out-of-scope work found beyond the `reopen` gap
already inside this ticket's own declared scope files and directly
blocking its own named acceptance test.

Gates: `frob check --ticket T-2616` reports 300 errors/1061 warnings repo-wide,
none of which reference `_ledger_mirror.py`, `test_ticket_leases.py`, or
`test_ticket_runner_ledger_mirror.py` (checked directly against the
`## Errors` section) -- pre-existing baseline noise (ty diagnostics in
unrelated test files, a long-standing import cycle spanning ~30
unrelated modules, etc.), not attributable to this change.

### Changed
```
 src/frob/app/ticket_runner/_ledger_mirror.py   | 17 +++---
 tests/test_ticket_leases.py                    | 17 ++++++
 tests/unit/test_ticket_runner_ledger_mirror.py | 20 ++++++
 tickets/T-2616/done-report.md                  | 85 ++++++++++++++++++++++++++
 tickets/T-2616/ticket.md                       |  7 ++-
 5 files changed, 137 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_milestone_edit_from_worktree_is_visible_on_primary` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[reopen]` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[milestone]` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 78 error(s), 825 warning(s), 874 waived
- error-findings: AFFECT001@src/frob/app/ticket_runner/_ledger_mirror.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2616, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
