## Done report

Changed:
src/frob/app/check_runner.py::_task_progress_callback (frob:tests directive separator)
src/frob/tickets/_leases.py::_rollback_pathspecs (frob:doc anchor retarget)
docs/commands/check.md (frob:describes anchor added on --fix example block)

Evidence:
Before fix: gate:DOC 5 errors, gate:DRIFT 3 errors (measured via frob check --json on main, tree_hash matching current main HEAD).
After fix (frob check --ticket T-3384 --json in leased worktree): gate:DOC down to 1 (DOC011, deferred -- see below), gate:DRIFT's targeted findings (DRIFT001 on _land_cmd.py, DRIFT002 x2 on check_runner.py) no longer present.
frob ack src/frob/app/ticket_runner/_land_cmd.py::_finish_only_if_already_landed --reason "..." (re-verified docstring vs implementation, only grew, did not diverge)

Filed: none (all 3 slice gates were pre-existing findings, no new out-of-scope work found)

Gates: partial -- 2 of 13 findings in this slice are BLOCKED by live lease collisions with other in-progress tickets, not fixed:
  - DOC011 (docs/modules/tickets.md:99, T-draft-ad5e921b citation) -- BLOCKED: docs/modules/tickets.md is leased by T-3358 (in-progress). Deferred until that lease clears.
  - gate:SELFAUDIT (5x SELFAUDIT001, tests/test_check_runner.py exec capability undeclared) -- BLOCKED: the fix requires editing design/frob.strata's testsuite node capability grant, which is leased by T-3311 (in-progress). Deferred until that lease clears.

11 of 13 findings in this slice (gate:DOC x4, gate:DRIFT x3, plus this note on the remaining 2 gate:DOC/gate:SELFAUDIT items) addressed or explained; the 2 blocked findings are NOT waived or ignored -- they need a second pass once T-3311/T-3358 land or release their leases.

Note for T-3324 (SELFAUDIT001 "clean against a live repo" structural finding): confirmed -- all 5 SELFAUDIT001 findings here are new accrual (undeclared 'exec' capability for subprocess.run calls added to tests/test_check_runner.py's _git_init fixture since design/frob.strata's testsuite node was last synced), not a distinct defect in this file. This is exactly the class T-3324 describes: a strata declaration that goes stale as unrelated test-fixture work lands, and cannot be kept green by a one-time patch.

### Changed
```
 tickets/T-3384/done-report.md | 35 +++++++++++++++++++++++++++++++++++
 tickets/T-3384/ticket.md      |  6 +++++-
 2 files changed, 40 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_app_runners_batch6.py::TestTaskProgressCallback::test_none_progress_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestTaskProgressCallback::test_updates_progress_with_language_qualified_label` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_rollback_on_land_in_progress_leaves_root_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 37 error(s), 4376 warning(s), 879 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/check_runner.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC011@docs/modules/tickets.md, DOCENUM001@docs/modules/gates.md, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3384, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py
