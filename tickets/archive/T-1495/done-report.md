## Done report

The 2026-08-04 incident: `frob ticket land T-1464` was SIGTERM-killed at
the 540s foreground timeout after its land commits were already on main
but before post-land verification finished; a LATER `frob ticket land`
invocation's unwind path performed a `reset --hard` that silently
discarded those already-completed commits, and earlier in the same
session ate two more (T-1199/T-1200 queue-drain commits) plus an
interleaved manual `frob ticket drop` commit.

Investigated every `git reset --hard` site in src/frob/tickets/_land*.py.
Two of the four (`_verified_reset_root` in _land_git_ops.py,
`_reconcile_one_land_repair_marker`'s crash-repair reset in _land.py)
already carry a tip-equality drift check (T-0907) that refuses instead
of resetting on any drift -- these were already safe against this
incident class. The THIRD, `_land_plan_reset_hard` (land_plan's own
unwind primitive, used by every land_plan failure path after a
successful merge -- merge/finalize failure, a dirty check_ticks()
result, or a dry-run), had NO check at all: it reset unconditionally to
whatever sha the caller passed, regardless of what root's tip had
become since. This is the concrete instance of T-1495's point 1/3 the
ticket asked to be found.

Implemented, exactly the acceptance sketch's "unwind boundary
assertion": before any reset, verify every commit about to be discarded
was authored by THIS land run, refuse loudly otherwise.

- _assert_reset_only_discards_own_commits(root, base_sha, own_commits)
  verifies root's CURRENT tip equals own_commits[-1] (the last commit
  THIS run's own steps produced), or base_sha if own_commits is empty.
  Tip equality, not a rev-list commit-set diff, is deliberate: a
  --no-ff merge's second-parent history (the worktree branch's own
  prior commits, e.g. a ticket-creation commit made before the merge
  ever ran) is legitimately part of this run's own merge, not a
  foreign interloper, even though a naive set-membership check flags
  it as "not ours" -- a first implementation attempt hit exactly this
  false positive (caught by the existing TestLandPlan suite) before
  landing on tip equality, which is also the SAME contract
  _verified_reset_root/T-0907 already established, generalized here
  to the expected FINAL tip a multi-commit run built up rather than
  just its starting one.
- _land_plan_reset_hard now takes own_commits and runs the assertion
  before resetting, returning Result[None, LandError] (was bare None)
  so a refusal is visible to the caller instead of silently discarding
  nothing.
- _land_plan_merge_and_finalize is a new split (ARCH001: kept
  _land_plan_locked under the 60-line threshold) of the merge-then-
  finalize-drafts half of _land_plan_locked's body: returns
  (result, own_commits) as a PAIR always, not just on success, so a
  partial failure (merge succeeded, finalize failed) still carries the
  merge commit's own sha forward into the caller's unwind -- losing
  track of it there would have reintroduced exactly the false-refusal/
  false-safety gap this ticket closes.
- Every _land_plan_reset_hard call site in _land_plan_locked now
  threads own_commits through and propagates a refusal.

Verified directly: a new test
(TestLandPlanUnwindNeverDiscardsForeignCommits.
test_foreign_commit_after_own_last_commit_refuses_instead_of_discarding)
has check_ticks() itself commit a foreign file to root mid-run (exactly
the interleaving shape of the incident) before returning False --
before this fix, land_plan's own unwind would have reset root back
past that foreign commit; after the fix, land_plan REFUSES
(Err(LandError.GitFailed)) and the foreign commit survives on root's
tip. The companion test confirms the ordinary non-interleaved unwind
path is unaffected.

Scope disclosure: this closes point 1/3 (the concretely-identified
unguarded land_plan unwind) of T-1495's four-point root-cause surface.
Points 2 (queue-drain commit durability across a same-invocation later
failure) and 4 (checkpointing or splitting post-land verification so a
>540s kill is always safe) each need a real design decision beyond a
mechanical unwind-boundary assertion -- both filed as drafts rather
than forced into this diff: T-1522 (queue-drain durability)
and T-1523 (checkpoint/split verification).

Also did NOT touch _land_locked's own unwind paths (the primary
per-ticket land path, distinct from land_plan): every one of those
already routes through _verified_reset_root, which already carries the
T-0907 tip-equality check -- confirmed by direct code reading, not
guessed. The gap this ticket closes was specific to land_plan's
previously-unchecked path.

### Changed
```
 design/frob.strata                        |  13 +-
 docs/guides/install.md                    |  49 ++++
 frob.lock                                 |   2 +-
 src/frob/app/ticket_runner/_land_cmd.py   | 249 +++++++++++++++++---
 src/frob/doctor.py                        | 113 ++++++++-
 src/frob/tickets/_land.py                 | 378 ++++++++++++++++++++++++++----
 src/frob/tickets/_land_squash.py          |  57 ++++-
 src/frob/tickets/_models.py               |  16 ++
 tests/system/test_cli_doctor.py           | 108 +++++++++
 tests/test_ticket_land.py                 | 241 +++++++++++++++++++
 tests/test_ticket_work_and_land_finish.py | 159 ++++++++++++-
 tickets.md                                | 353 +++++++++++++++++++++++++++-
 12 files changed, 1641 insertions(+), 97 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits::test_foreign_commit_after_own_last_commit_refuses_instead_of_discarding` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits::test_no_foreign_commit_unwinds_to_the_merge_commit_not_pre_merge` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 6 error(s), 139 warning(s), 781 waived
- error-findings: AFFECT001@src/frob/tickets/_land.py, AFFECT001@src/frob/tickets/_models.py, DOC002@src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1513/src/frob/doctor.py:348, E501@/home/logan/projects/frob/.claude/worktrees/t-1513/src/frob/tickets/_land.py:1090, SEC110@src/frob/tickets/_land.py
