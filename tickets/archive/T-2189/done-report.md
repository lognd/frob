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
