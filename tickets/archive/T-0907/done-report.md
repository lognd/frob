## Done report

Root cause: every unwind path in `land()`'s squash-apply stage used a
BARE `git reset --hard` (target defaults to whatever `HEAD` resolves to
AT RESET TIME). If root's HEAD/ref got corrupted mid-run by a kill (a
torn ref-update from an interrupted git subprocess sharing the kill's
process group), the bare reset cements that corruption instead of
restoring a known-good state -- the observed ~60-commit regression.

Fix, closing both fix requirements and acceptance criteria 0/1:
1. `_verified_reset_root` replaces every bare unwind: resets to an
   EXPLICIT sha (`pre_land_tip`, captured via `git rev-parse HEAD` once
   at the run's start, threaded through as a plain local value, never
   stored in shared `.frob` state) and refuses loudly (no reset
   performed) if root's current tip has already drifted from that
   recorded value.
2. A land-repair marker (`root/.frob/land-repair/<ticket_id>.json`,
   recording `pre_land_tip`) is written right before `_land_squash_apply`
   starts mutating root and cleared in a `finally` on any exit. This
   survives an uncatchable SIGKILL (a Python signal handler cannot trap
   it -- the "leave an explicit marker the next invocation repairs" half
   of fix requirement 3), and `_repair_stale_land_marker` reconciles
   ALL such leftover markers under root at the START of the next
   `land()` call -- resetting to the recorded tip if it still matches
   root's current tip, or refusing loudly (leaving the marker for manual
   inspection) if it has drifted. The repair scans the whole marker
   directory rather than keying off the caller's own ticket_id, since a
   crash after finalize renames a draft id to its real sequential id and
   a human's natural retry uses the finalized id (matching the existing
   T-0795 retry precedent, `TestLandRetryAfterFinalizeThenFail`).

Changed: `src/frob/tickets/_land.py`'s `_verified_reset_root`,
`_write_land_repair_marker`, `_clear_land_repair_marker`,
`_repair_stale_land_marker`, `_land_repair_dir`,
`_land_repair_marker_path`, `_check_squash_conflicted`,
`_squash_and_splice_ledger`, `_assert_land_complete`,
`_apply_release_bump`, `_land_squash_apply`, `_land_locked`.

Evidence (6 pytest node ids, bound to acceptance criteria 0/1 as shown
above):
- tests/test_ticket_land.py::TestVerifiedResetRoot::test_resets_to_the_explicit_pre_land_tip_when_current_matches
- tests/test_ticket_land.py::TestVerifiedResetRoot::test_refuses_and_does_not_reset_when_current_tip_has_drifted
- tests/test_ticket_land.py::TestLandRepairMarker::test_no_marker_is_a_silent_no_op
- tests/test_ticket_land.py::TestLandRepairMarker::test_repair_resets_root_when_current_tip_matches_the_marker
- tests/test_ticket_land.py::TestLandRepairMarker::test_repair_refuses_loudly_when_current_tip_has_drifted_from_the_marker
- tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry
  (real SIGKILL delivered mid-squash-apply via a forked child process;
  asserts root's tip is unchanged after the kill and a retry lands
  cleanly)

Filed: none.

Gates: `frob check --ticket T-0907 --only gates-fast` (0 errors),
`--only gates-native` (0 errors), `--only gates-security` (0 errors),
`--only static` (0 errors); `frob test --base main` selected+ran 7
python test(s), exit=0; full `pytest tests/test_ticket_land.py` (121
tests) passes.
