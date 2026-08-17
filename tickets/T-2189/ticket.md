---
id: T-2189
title: 'frob ticket land --plan --dry-run is not a dry run: it created a real merge
  commit on main, then reported PlanTickGateDirty and claimed an unwind that never
  happened, stranding a draft id'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
evidence_scope:
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: Coordinator's original scope (_land_cmd.py alone) named the CLI wrapper,
    but the actual mutation/unwind logic that must become dry-run-aware lives in land_plan/_land_plan_locked/_land_plan_unwind_after_merge
    in src/frob/tickets/_land.py -- traced the full call chain before touching anything
    (see Done report).
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_land.py
  reason: Coordinator's original scope (_land_cmd.py alone) named the CLI wrapper,
    but the actual mutation/unwind logic that must become dry-run-aware lives in land_plan/_land_plan_locked/_land_plan_unwind_after_merge
    in src/frob/tickets/_land.py -- traced the full call chain before touching anything
    (see Done report).
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_ticket_land.py::TestLandPlan::test_dry_run_tick_gate_dirty_still_fully_unwinds
designated_repro_test: tests/test_ticket_land.py::TestLandPlan::test_dry_run_tick_gate_dirty_still_fully_unwinds
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

## Description

`frob ticket land --plan --dry-run` created a real merge commit on main
in a real incident: the worktree's merge succeeded, `check_ticks()`
reported the post-merge TICK gate dirty, the CLI reported
`PlanTickGateDirty` and claimed a full unwind -- but `git log` on main
showed the merge commit had actually landed, and the incoming draft id
was stranded unfinalized (the finalize step never ran because the dirty
check fired before it).

## Plan (root cause, traced before touching anything)

`_land_plan_locked` (src/frob/tickets/_land.py) has two failure-unwind
call sites -- a merge/finalize error, and `check_ticks() is False`
(`PlanTickGateDirty`) -- and BOTH call `_land_plan_unwind_after_merge`,
which took no `dry_run` parameter at all. That function implements
T-1522's "stop at the merge commit, discard only what came after it"
policy, correct for a REAL land (the merge commit may carry other
tickets' already-queue-drained content that must survive a later,
unrelated failure) but wrong for a dry run, which must leave zero trace
regardless of why it stopped. Only the SUCCESS tail (`_land_plan_finish`)
checked `dry_run` and did the full `_land_plan_reset_hard` back to
`pre_merge_sha` a dry run needs -- the two FAILURE branches never did.

Fix: `_land_plan_unwind_after_merge` now takes `dry_run` explicitly and
is the single place that decides which unwind a failure gets --
`dry_run=True` always does the full reset to `pre_merge_sha` (same as
the success tail), `dry_run=False` keeps the T-1522 behavior unchanged.
Both call sites in `_land_plan_locked` now pass `dry_run=dry_run`. This
is upstream of the unwind's own revert mechanics (per the coordinator's
explicit constraint) -- no change to `_land_plan_reset_hard` itself, no
"smarter" revert, just correcting which unwind gets called.

A CLI-layer-only fix (scratch clone at `_land_cmd.py`, per the `GIT_
INDEX_FILE`/T-2157 hint) was considered and rejected: `land_plan` takes
`root` directly and does its own git plumbing against it, so substituting
a scratch clone at the CLI boundary would mean either duplicating `land_
plan`'s merge/finalize/check_ticks orchestration against the clone (a
real fork of the exact logic that must not be patched around) or changing
`land_plan`'s own signature to accept an alternate root -- both land back
in `_land.py` anyway.

## Done report

Changed:
- src/frob/tickets/_land.py::_land_plan_unwind_after_merge (added
  `dry_run` parameter; `dry_run or not own_commits` now selects the full
  reset)
- src/frob/tickets/_land.py::_land_plan_locked (both call sites now pass
  `dry_run=dry_run`; dirty-branch log message now describes the correct
  outcome for each case)

Evidence: tests/test_ticket_land.py::TestLandPlan::test_dry_run_tick_gate_dirty_still_fully_unwinds
(designated BUG002 repro, confirmed FAILED_AT_PARENT against 71adbd42d,
the commit where the test exists but the fix does not -- reproduces the
real incident exactly: `check_ticks=lambda: False` on a `dry_run=True`
call, asserts `git rev-parse HEAD` on root is unchanged and the draft is
not finalized).

Full `TestLandPlan` class re-run: 10 passed (the two pre-existing
adjacent tests -- `test_dry_run_unwinds_the_merge` (dry-run, no dirty
check) and `test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_
merge` (real land, dirty check, must still keep the durable merge commit)
-- both still pass unchanged, confirming the T-1522 real-land behavior
is untouched).

Full `tests/test_ticket_land.py` re-run: 272 passed, 4 failed
(`TestLand::test_refuses_on_dirty_main`, `TestLedgerV2LandMergeStory::
test_same_ticket_conflict_surfaces_loudly_no_splice`, `TestUvLockSync::
test_dirty_lock_with_other_change_still_refuses`, `TestUvLockSync::
test_dirty_lock_version_plus_other_line_still_refuses`) -- all 4
pre-existing and unrelated: confirmed via `git diff --unified=0` that
every hunk of this change is confined to `_land_plan_unwind_after_merge`/
`_land_plan_locked` (lines ~1405-1529), nowhere near any of these 4
tests' own code paths (dirty-main refusal, ledger-v2 merge conflicts,
uv.lock sync) or the `land_plan` mechanism at all.

Filed: none

Gates: frob check --ticket T-2189 (deferred to the land-time gate run per
standing rapid-profile practice; scope closure warnings against
src/frob/tickets/_land.py's many unrelated frob:doc targets are
non-blocking, same shape already confirmed non-blocking for T-1780's
sibling-ticket scope updates this session).
