## Done report

ROOT CAUSE confirmed exactly as the ticket described: land's staging is
not transactional. Two SEPARATE unwind mechanisms exist in this codebase
(`_verified_reset_root`, T-0907, for the main squash-apply pipeline; and
`_assert_reset_only_discards_own_commits`/`_land_plan_reset_hard`, T-1495,
for `land --plan`'s own path) and BOTH had the identical gap: on
detecting that root's tip drifted from what this run started with, they
correctly refuse to blindly `reset --hard` (which could destroy the
concurrent commit that caused the drift) -- but neither one unstaged
anything before returning the refusal, leaving whatever this run had
already staged sitting in root's index for the next unrelated `git
commit` to sweep up. That is exactly the 2026-08-07 T-1688 incident.

## Audit (required deliverable, not just the fix)

Every early-return in the squash-apply pipeline that runs AFTER `git
merge --squash --no-commit` has staged content in root, counted by
grepping every call site of the shared unwind primitive:

- 14 call sites of `_verified_reset_root` across `_land_squash.py`
  (`_check_squash_conflicted`/`_check_squash_conflicted_v2` x2 each,
  `_unwind_squash_apply`, `_refuse_if_land_regresses_terminal_state`,
  `_assert_land_complete` x3, `_apply_pre_commit_sweep_or_unwind`) and
  `_land_release.py` (`_apply_release_bump` x3,
  `_apply_gate_rule_sync`) -- ALL 14 already called `_verified_reset_
  root` correctly before this ticket; they get the T-1740 unstage-on-
  drift fix automatically since it lives in the ONE shared primitive
  they all funnel through.
- 1 GENUINE GAP found and fixed: `_commit_squash_apply` (the actual
  final `git commit` of the staged squash) had NO unwind call at all on
  its own failure -- it only logged instructions telling a human to
  clean up root by hand. This is the ticket's own T-1688 incident shape
  almost exactly (a refusal partway through the very last step). Fixed:
  attempts `_verified_reset_root` first, falls back to
  `_unstage_index_only` if that itself reports drift.
- 1 SECOND unwind mechanism found with the identical gap: `land --plan`
  (T-1269/T-1495) runs its own, separate `_assert_reset_only_discards_
  own_commits`/`_land_plan_reset_hard` pair, which had the SAME
  drift-detected-but-does-not-unstage gap. Fixed the same way.

Total: 16 call sites now covered end to end, 2 of which (the two "last
step of a pipeline" cases) needed a direct fix; the other 14 needed
nothing because the ONE shared primitive they call was the actual fix
site.

## The three required pieces

1. **Land must unstage what it staged on every refusal path.** Fixed via
   `_unstage_index_only` (`git reset`, bare/mixed, no target -- clears
   the index back to matching current `HEAD` without moving `HEAD` or
   touching a single working-tree byte, so it is safe to call even when
   a full `reset --hard` is not), called from `_verified_reset_root`'s
   drift branch (split into `_refuse_drift_but_unstage` to clear
   ARCH001), `_commit_squash_apply`'s own failure path, and
   `_assert_reset_only_discards_own_commits`'s refusal in `_land.py`.

2. **Refuse on entry if root's index already holds staged content.**
   Investigated and found ALREADY STRUCTURALLY TRUE, not a new check
   needed: `_refuse_if_main_dirty` (called first thing in
   `_land_precheck`, strictly before any git mutation) uses
   `_porcelain_dirty`, which is a bare `git status --porcelain` --
   that reports BOTH staged (index) and unstaged (working-tree) state
   uniformly, so a leftover staged index from a prior refused land was
   ALREADY refusing the next `land` attempt via `DirtyMain`. What was
   missing was #3.

3. **DirtyMain's message should name staged state explicitly.** Fixed:
   `_porcelain_dirty_paths_staged` (new) classifies the porcelain output
   by its index-status column; `describe_root_dirt` now leads with "N
   STAGED (likely a prior land's leftover index, T-1740)" whenever any
   dirty path is staged, instead of the old undifferentiated
   "uncommitted changes" wording that sent an agent looking for
   working-tree edits when the real cause was a leftover staged index.

Relationship to T-1615 (coordinated per the ticket's own note, not
duplicated): T-1615 makes every ordinary ledger-writing verb
(`block`/`scope`/`priority`/...) auto-commit uniformly, which is what
would have prevented the ROOT incident this ticket is about --  a
coordinator's manual `git add -A tickets.md && git commit` in a shared
root. Once T-1615 lands, that manual commit pattern largely disappears
and this hazard's blast radius shrinks with it. This ticket's own fix
(land unstages what IT staged) is orthogonal and still needed regardless
-- it protects against ANY bare commit in root while a land is stuck
mid-refusal, not just the specific manual-ledger-commit pattern T-1615
removes.

Evidence: tests/test_ticket_land.py::TestVerifiedResetRoot's 4 tests (unstage primitive + both drift branches), TestDescribeRootDirtNamesStagedState's 3 tests (staged-vs-unstaged message distinction), TestCommitSquashApplyUnwindsOnCommitFailure's 1 test (the genuine gap fixed), TestLandPlanUnwindNeverDiscardsForeignCommits's 2 tests (the --plan path's own instance of the same gap, plus the pre-existing T-1495 regression lock re-verified still passing).

Filed: none (grepped `frob ticket list` for "staged"/"index"/"land
unstage" first; no duplicates).

Gates: `frob check --ticket T-1740` clean for this ticket's own diff
(gate:ARCH/COV/SCOPE/AFFECT/SEC all pass after the ARCH001 line-count fix
via `_refuse_drift_but_unstage`; ruff-check/ty both clean). The COV002
findings this run also surfaced against `_leases.py`/`design/frob.strata`
are T-1615's own stacked, uncommitted-to-main work sharing this same
worktree branch (T-1615 is still `queued`, blocked on a lease conflict
with T-1727 over `docs/modules/tickets.md`) -- unrelated to and
predating this ticket's own diff, not something T-1740 introduced or is
responsible for. `frob test --base main` and the full
`tests/test_ticket_land.py` suite: 248 passed, 0 failed.

### Changed
```
 docs/modules/tickets.md           |  12 ++-
 rapid-debt.jsonl                  |   2 +
 src/frob/tickets/_land.py         |  21 +++-
 src/frob/tickets/_land_git_ops.py | 183 ++++++++++++++++++++++++--------
 src/frob/tickets/_land_squash.py  |  40 +++++--
 tests/test_ticket_land.py         | 159 +++++++++++++++++++++++++++
 tickets.md                        | 218 +++++++++++++++++++++++++++++++++++++-
 7 files changed, 580 insertions(+), 55 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestVerifiedResetRoot::test_drift_refusal_still_unstages_the_index` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestVerifiedResetRoot::test_unstage_index_only_never_moves_head_or_touches_tracked_content` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestVerifiedResetRoot::test_resets_to_the_explicit_pre_land_tip_when_current_matches` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestVerifiedResetRoot::test_refuses_and_does_not_reset_when_current_tip_has_drifted` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDescribeRootDirtNamesStagedState::test_staged_dirt_is_called_out_explicitly` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDescribeRootDirtNamesStagedState::test_working_tree_only_dirt_is_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDescribeRootDirtNamesStagedState::test_porcelain_dirty_paths_staged_only_reports_index_status` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommitSquashApplyUnwindsOnCommitFailure::test_commit_failure_unwinds_the_staged_squash` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits::test_foreign_commit_refusal_still_unstages_own_leftover_content` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits::test_foreign_commit_after_own_last_commit_refuses_instead_of_discarding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 0 error(s), 358 warning(s), 723 waived
- error-findings: none (measured, zero errors)
