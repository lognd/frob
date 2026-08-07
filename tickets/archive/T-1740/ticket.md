---
id: T-1740
title: A refused land leaves its merged files STAGED in root's index; the next bare
  git commit publishes another agent's work
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_land_squash.py
- tests/test_ticket_land.py
- src/frob/tickets/_land_release.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_release.py
  reason: the T-0907 mid-staging-drift unwind-refusal lives in _verified_reset_root
    (_land_git_ops.py, already in scope) but _apply_release_bump's own unwind call
    sites are in _land_release.py
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_ticket_land.py::TestVerifiedResetRoot::test_drift_refusal_still_unstages_the_index
- tests/test_ticket_land.py::TestVerifiedResetRoot::test_unstage_index_only_never_moves_head_or_touches_tracked_content
- tests/test_ticket_land.py::TestVerifiedResetRoot::test_resets_to_the_explicit_pre_land_tip_when_current_matches
- tests/test_ticket_land.py::TestVerifiedResetRoot::test_refuses_and_does_not_reset_when_current_tip_has_drifted
- tests/test_ticket_land.py::TestDescribeRootDirtNamesStagedState::test_staged_dirt_is_called_out_explicitly
- tests/test_ticket_land.py::TestDescribeRootDirtNamesStagedState::test_working_tree_only_dirt_is_unchanged
- tests/test_ticket_land.py::TestDescribeRootDirtNamesStagedState::test_porcelain_dirty_paths_staged_only_reports_index_status
- tests/test_ticket_land.py::TestCommitSquashApplyUnwindsOnCommitFailure::test_commit_failure_unwinds_the_staged_squash
- tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits::test_foreign_commit_refusal_still_unstages_own_leftover_content
- tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits::test_foreign_commit_after_own_last_commit_refuses_instead_of_discarding
designated_repro_test: null
threat: null
component: null
---
A `frob ticket land` that refuses partway through leaves the files it had
already merged and staged sitting in ROOT'S GIT INDEX. Nothing cleans
them up, and the next person to run `git commit` in root publishes them
under whatever message they were writing.

That is not hypothetical. On 2026-08-07 it happened, to the coordinator,
with a live agent's in-flight work:

1. Agent A's `land T-1688` merged its worktree branch into root and
   staged the result, then refused at the REL001 bump with T-0907
   (mid-staging drift). Correct refusal -- but it left 14 files staged in
   root's index, including 440 lines of `_worker.py` and its tests.
2. The coordinator, unaware, ran `git add -A tickets.md` (correctly
   scoped) followed by a BARE `git commit -m "chore(tickets): requeue
   T-1720 and file the wave ticket"`. A bare commit takes the WHOLE
   INDEX, not the paths just added. Agent A's entire T-1688
   implementation -- 1416 insertions across 14 files -- was published
   under an unrelated chore message.
3. That commit moved root's tip, so agent A's SUBSEQUENT land attempts
   failed with the same mid-staging drift, repeatedly. The coordinator
   caused the blocker it was later asked to clear.
4. The eventual real land committed only the release artifacts, because
   the code was already in. `git log --diff-filter=A` attributes
   `_worker.py` to a chore commit about requeuing an unrelated ticket.

Nothing was lost and main is green, but the history now misattributes a
440-line module, and roughly an hour of a live agent's time was spent
blocked on a state the coordinator created.

ROOT CAUSE: land's staging is not transactional. It stages, then
validates, and on validation failure it refuses WITHOUT unstaging. The
index is shared mutable state on a checkout that concurrent agents and a
human are both using.

REQUIRED:

1. LAND MUST UNSTAGE WHAT IT STAGED ON EVERY REFUSAL PATH. Snapshot the
   index state on entry; on any refusal, restore it. A refusal that
   leaves the workspace altered is not a refusal, it is a partial apply
   with an error message. Every early-return in the land pipeline needs
   this, not just the T-0907 one -- audit them all and say how many there
   were.
2. On entry, land should REFUSE if root's index is already dirty with
   staged content it did not put there, naming the paths -- the same way
   `_refuse_if_main_dirty` handles the working tree. A pre-staged index
   is exactly as dangerous as a dirty tree and is currently unchecked.
3. The DirtyMain check should cover STAGED-but-uncommitted state
   explicitly in its message. Today it reports "uncommitted changes",
   which reads as working-tree edits and sent an agent looking for the
   wrong thing.

SECONDARY, and worth its own consideration: a `frob` verb for a scoped
ledger commit, so a coordinator never types a bare `git commit` in a
shared root at all. T-1615 is already making every ledger-writing verb
auto-commit; if that lands first, the coordinator's manual commit largely
disappears and this hazard shrinks with it. Coordinate rather than
duplicate.

Note the irony as a design constraint, not a joke: T-1698's own body
states "a blanket `git add -A` on a root checkout that concurrent lands
are racing against would sweep up whatever another agent had in flight."
That hazard was identified, written down as a requirement for the CODE,
and then committed by hand anyway through a slightly different mechanism.
A rule that exists only as prose in a ticket body protects nothing.