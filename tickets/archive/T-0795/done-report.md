## Done report

Two fixes in src/frob/tickets/_land.py, both wired through _land_precheck /
_close_finalized_ticket (no LandError enum change, no ticket_runner.py change
needed -- root is already CLI-cwd-derived, the fix belongs entirely in land()'s
own precheck/close path in _land.py).

1. Idempotent retry after own finalize: _close_finalized_ticket now loads
   `final_id` FIRST and checks its state before calling transition(). If
   already TicketState.DONE (a prior land() attempt reached finalize+close,
   committed that in the worktree, then failed at a LATER step -- squash
   conflict, REL001 bump, or the T-0463 completeness assertion, all of which
   unwind ONLY root via reset --hard, leaving the worktree's done commit
   intact), it logs and returns Ok(final_id) directly instead of re-running
   transition(..., DONE), which used to error InvalidTransition (done has no
   done->done edge in _TRANSITIONS) every time. A non-done ticket still runs
   the real transition unchanged (covered by a companion sanity test).

2. Early cwd-inside-worktree refusal: new _refuse_if_root_is_worktree, called
   first in _land_precheck (before the dirty-main check, before any git
   mutation). If root == worktree (both already .resolve()d by land()), it
   refuses with Err(LandError.IncompleteLand) and a log message naming the
   actual likely cause (root defaults to the invoker's cwd, so running `frob
   ticket land` from inside the worktree makes root resolve to worktree for
   free) and the remedy (run from the root checkout). Reuses the existing
   IncompleteLand enum tag deliberately (the log message carries the
   corrected diagnosis, not a new enum) so the pre-existing T-0761 regression
   test (renamed/preserved as
   TestLandRefusesWhenRootIsWorktree::test_still_refuses_when_worktree_has_diverged_commits)
   stays green under the new, earlier, more specific check. The genuinely
   distinct T-0640/T-0761 diagnosis in _worktree_full_changeset (merge-base
   == HEAD for a DISTINCT worktree path pointed at the same branch) is
   untouched and still fires for that separate condition.

Changed:
  src/frob/tickets/_land.py::_refuse_if_root_is_worktree (new)
  src/frob/tickets/_land.py::_land_precheck (calls the new check first)
  src/frob/tickets/_land.py::_close_finalized_ticket (idempotent DONE check)
  tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail (new, 2 tests)
  tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree (new, 2 tests)

Evidence:
  tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_after_finalize_then_squash_failure_lands_the_diff
  tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_when_still_queued_re_runs_the_ordinary_transition
  tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_refused_before_any_git_mutation_names_the_real_mistake
  tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_still_refuses_when_worktree_has_diverged_commits
  (bound to acceptance[0] via --accepts 0)

  `uv run --frozen pytest tests/test_ticket_land.py -q` -> 66 passed (62
  pre-existing + 4 new); every pre-existing test, including the T-0761
  same-branch regression, still green.
  `uv run --frozen frob test --base main` -> run_selected: python exit=0
  duration=7.01s [PASS], selecting tests/test_ticket_land.py (whole file) +
  the 4 new node ids + tests/test_tickets.py::test_tickets_queue_workflow_integration.

Filed: none -- no out-of-scope work discovered.

Gates: `uv run --frozen frob check --ticket T-0795` chunked via `--only
lint|static|gates-fast|gates-native|gates-security` (the standard chunked
loop, T-0627) -- 0 errors in every stage after a `ruff format` pass and a
`frob ticket sweep T-0795` refresh (PRE001 was stale from the pre-work sweep
taken before implementation started). No waivers added for this ticket's own
code; touched functions carry frob:tests directives to their new regression
tests.

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_after_finalize_then_squash_failure_lands_the_diff` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_when_still_queued_re_runs_the_ordinary_transition` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_refused_before_any_git_mutation_names_the_real_mistake` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree::test_still_refuses_when_worktree_has_diverged_commits` (pytest node id, verified passing when recorded)
