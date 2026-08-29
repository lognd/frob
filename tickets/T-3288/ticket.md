---
id: T-3288
title: 'frob ticket land --finish DELETED a worktree without merging: the T-2108 shortcut
  trusts main''s ledger state instead of branch ancestry'
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_work_and_land_finish.py
- tests/unit/test_land_finish_guard.py
- tests/unit/test_land_finish_idempotent.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: test files updated for the new required verified_landed kwarg and third-fixture
    coverage
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_land_finish_guard.py
  reason: test files updated for the new required verified_landed kwarg and third-fixture
    coverage
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_land_finish_idempotent.py
  reason: test files updated for the new required verified_landed kwarg and third-fixture
    coverage
  actor: logan
  at: '2026-08-28'
evidence:
- tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_terminal_on_main_skips_land_core_and_cleans_up
- tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_non_terminal_on_main_runs_the_normal_land
- tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_done_on_main_but_content_not_confirmed_runs_the_normal_land
- tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_removes_a_worktree_with_no_live_process
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_finish_removes_the_worktree
designated_repro_test: tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_done_on_main_but_content_not_confirmed_runs_the_normal_land
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
WORK-DESTROYING BUG, reported from real consumer use (../diax FROBLEMS.md
F-034, marked "serious" by the reporter). Recovery was possible ONLY because a
branch happened to survive.

WHAT HAPPENED, in the reporter's words and sequence:

    frob ticket land T-0027 --worktree ... --finish

printed

    "T-0027 is already 'done' on main -- skipping a full re-land (T-2108...)
     and running pure cleanup only"

then REMOVED THE WORKTREE and exited 0, with no LAND-PROOF line. main had NONE
of the ticket's code -- `src/diax/model/` was absent entirely. The only reason
the work still exists is that branch `t-0027` was not deleted with the
worktree; recovery was a manual `git merge` under FROB_LAND_INTERNAL=1.

THE ROOT CAUSE IS ALREADY DIAGNOSED, and the diagnosis is precise: the T-2108
shortcut decides "already landed" from the LEDGER STATE on main, not from
whether the branch head is an ancestor of main. Those are different facts, and
this repo has been bitten by exactly that distinction before -- there is prior
art where a land proof verified ancestry rather than content and reported
verified=True for a commit containing none of the ticket's code. This is the
same confusion pointed the other way.

WHY THE LEDGER SAID `done` WITH NO CODE ON MAIN -- see F-033, which is the
enabling half and should be fixed with it or before it. `frob ticket close`
inside a worktree MIRRORS state and evidence onto main immediately, while the
code stays on the branch until land. So between close and land, main
legitimately reads `state: done` with N evidence ids for a ticket whose code is
nowhere on main. The reporter also saw the downstream damage of that window:
`frob check` on main failing COV003 nine times because the cited evidence does
not resolve, `frob ticket doable` offering tickets blocked_by a ticket whose
code is not present, and a post-land sweep auto-filing a regression ticket
against work the repo never did.

TWO FIXES, BOTH REQUIRED, per the reporter's own analysis which I have not
improved on:
  1. The T-2108 "already done, pure cleanup" shortcut must test
     `is_ancestor_of_main(branch_head)`, NOT the ledger state.
  2. `--finish` must NEVER remove a worktree whose branch is not an ancestor of
     main. That is the backstop for every other way this reasoning could be
     wrong, and it is the one that would have prevented the incident on its own.

DO NOT FIX THIS BY MAKING `--finish` KEEP THE BRANCH AND CALL IT SAFE. A
surviving branch is what saved this user, but an invisible branch is also how
work gets silently lost here -- clean-but-unlanded branches are invisible to
most of this tooling. The fix is to refuse the destructive step, loudly, not to
leave a quiet escape hatch and hope someone notices.

ALSO CONSIDER, and state a decision either way: whether close should mirror
state/evidence at all before land, or mirror scope/lease only and keep
state+evidence on the branch until the land publishes them (the reporter's own
suggestion). That is the deeper fix and it removes the window rather than
guarding its edge. If it is too large for this ticket, file it and say so --
but do not fix only the shortcut and leave the window open, because the window
is what produces the false premise.

RELEASE RELEVANCE: the owner is preparing frob's first real PyPI release. This
is a command, documented in the agent workflow, that can delete a user's
uncommitted-to-main work while reporting success. It should not ship as-is.

MUST-FIRE FIXTURE: `--finish` against a worktree whose branch is NOT an
ancestor of main REFUSES, names the branch, and does not remove the worktree.
MUST-STAY-QUIET FIXTURE: `--finish` after a genuine successful land (branch IS
an ancestor) still cleans up exactly as today.
THIRD FIXTURE: a ticket whose ledger state on main is `done` but whose branch
is not an ancestor is treated as NOT landed by the T-2108 shortcut.

ACCEPTANCE
- The shortcut decides on ancestry, not ledger state.
- `--finish` cannot remove an unmerged worktree.
- All three fixtures present.
- A stated decision on the close-time mirroring window (fix here, or filed with
  reasoning).
- Verify no other caller of the same shortcut has the same premise; report the
  count.