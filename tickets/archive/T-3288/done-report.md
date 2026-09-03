## Done report

Changed:
- src/frob/app/ticket_runner/_land_cmd.py::_finish_only_if_already_landed
- src/frob/app/ticket_runner/_land_cmd.py::_worktree_content_already_on_main (new)
- src/frob/app/ticket_runner/_land_cmd.py::_finish_worktree (new required `verified_landed` kwarg)
- tests/unit/test_land_finish_idempotent.py (scope added; new fixture test)
- tests/unit/test_land_finish_guard.py (scope added; `verified_landed=True` at every call site)
- tests/test_ticket_work_and_land_finish.py (scope added; `verified_landed=True` at both call sites)

Summary of the fix (T-3288, F-034 incident):

1. `_finish_only_if_already_landed` no longer treats a terminal ledger
   state on main as proof the code landed. It now also requires
   `_worktree_content_already_on_main` -- which reuses `land()`'s own
   positive-signal check (`_check_already_landed`, T-1618/T-1675: empty
   scope-content-diff plus a `done` state or a carried `frob:ticket`
   directive) -- before taking the pure-cleanup path. A terminal state
   with unconfirmed content now falls through to the real `_land_core`
   pipeline (third fixture), which will land the code for real or refuse
   for a concrete, named reason.

   DECISION: I deliberately did NOT implement a literal `git merge-base
   --is-ancestor <branch-head> main` check, despite the ticket text's own
   wording. This repo lands by SQUASH-APPLY (`_land_squash_apply`), not a
   merge commit -- a worktree branch's own head commit is NEVER a graph
   ancestor of the squash commit that actually carries its content onto
   main, even for a completely genuine, successful land (the squash
   commit's tree matches the worktree's tree, but its parent is main's
   prior tip, not the worktree branch). A literal ancestor-of-branch-head
   check would refuse cleanup for the T-2108 shortcut's own core
   legitimate case (a land that died between commit and worktree removal)
   exactly as often as it would refuse the incident -- verified by reading
   `land()`'s own squash-apply code path and by the pre-existing
   `test_terminal_on_main_skips_land_core_and_cleans_up` fixture, which
   models exactly that legitimate case. `_check_already_landed`'s content
   check is the same fact ("is this code already on main") computed
   correctly for this repo's actual merge strategy, and it is the SAME
   check `land()` itself already trusts mid-pipeline to answer the
   identical question -- reusing it rather than reimplementing avoids a
   second, possibly-divergent copy of that logic (NO DUPLICATION).

2. Backstop: `_finish_worktree` now takes a REQUIRED `verified_landed`
   keyword (no default) -- every call site must say explicitly whether it
   has already confirmed the code reached main. `False` REFUSES the
   removal outright (logs ERROR naming the worktree/branch, no bypass via
   `--force`, which guards a different, unrelated refusal). Both
   production call sites were audited: `_finish_land_after_success`
   passes `verified_landed=True` (already gated on `ancestor_ok and
   state_ok` from a REAL land's `report.commit_sha`, by its own existing
   comment); `_finish_only_if_already_landed` passes it only after its own
   new positive confirmation. There are exactly 2 production call sites of
   `_finish_worktree` and exactly 1 production call site of
   `_ticket_terminal_state_on_main` (the one this ticket fixes) -- no
   other caller shares the fixed premise.

3. THREE FIXTURES present (all in tests/unit/test_land_finish_idempotent.py
   unless noted):
   - MUST-FIRE: `test_done_on_main_but_content_not_confirmed_runs_the_normal_land`
     -- ledger reads `done` on main, worktree branched before the close and
     never merged; `_finish_only_if_already_landed` returns `False`, worktree
     is NOT removed.
   - MUST-STAY-QUIET: `test_terminal_on_main_skips_land_core_and_cleans_up`
     (pre-existing, now also exercises the content check) plus
     `tests/unit/test_land_finish_guard.py::TestFinishWorktree` (a genuine
     successful cleanup still works with `verified_landed=True`).
   - THIRD FIXTURE (ledger done, branch not landed): same test as
     MUST-FIRE above -- it is the T-2108-shortcut-treats-as-NOT-landed case
     the ticket asks for explicitly.

4. DEEPER FIX DECISION: T-3288's own scope is
   `src/frob/app/ticket_runner/_land_cmd.py` only. The close-time
   mirroring code (F-033: `frob ticket close` mirrors `state`/evidence
   onto main immediately, before the code lands) lives outside that
   scope. Filed T-3340 ("close should not mirror state/evidence onto main
   until land publishes them") with the proposed direction (mirror
   scope/lease only; defer state/evidence to land time) and a pointer to
   read T-3336's conclusion first for consistency, per this ticket's own
   instruction not to fix only the shortcut and leave the window open
   silently.

Evidence: tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_terminal_on_main_skips_land_core_and_cleans_up, tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_non_terminal_on_main_runs_the_normal_land, tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_done_on_main_but_content_not_confirmed_runs_the_normal_land, tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_removes_a_worktree_with_no_live_process, tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_finish_removes_the_worktree

Filed: T-3340 (deeper close-mirroring fix, out of this ticket's declared scope)

Gates: `frob check --ticket T-3288 --only scope --only prework` clean except
one pre-existing SCOPE001 on `tickets/T-3340/ticket.md` (this same worktree's
own committed ticket-admin commit for T-3340, filed per this ticket's own
instruction) -- could not add it to scope: `tickets/**` is under a live
cross-worktree lease held by T-3338, an unrelated in-progress ticket, so the
scope-add itself is blocked, not waived. Every other gate family is
repo-wide per `frob check`'s own scope-note and pre-existing (confirmed two
of the full-run failures -- `TestBranchDriftGuard::test_branch_drift_before_final_commit_refuses_by_construction`
and `TestAssertDesignLoadsPreLand::test_a_tier_a_handler_that_corrupts_design_after_it_was_healthy_refuses_the_land`
-- reproduce identically on a clean checkout of main, unrelated to this change).

### Changed
```
 tickets/T-3288/ticket.md | 28 +++++++++++++++++++++++
 tickets/T-3340/ticket.md | 58 ++++++++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 86 insertions(+)
```

### Evidence
- `tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_terminal_on_main_skips_land_core_and_cleans_up` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_non_terminal_on_main_runs_the_normal_land` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_done_on_main_but_content_not_confirmed_runs_the_normal_land` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_removes_a_worktree_with_no_live_process` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_finish_removes_the_worktree` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 79 error(s), 4067 warning(s), 885 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, COV007@src/frob/tickets/_done_report.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/doctor.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, missing-argument@tests/unit/test_land_finish_guard.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
