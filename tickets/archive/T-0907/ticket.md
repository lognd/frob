---
id: T-0907
title: killed land can reset main to a STALE tip (~60 commits lost off-branch; reflog
  reset moving-to-HEAD)
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestVerifiedResetRoot::test_resets_to_the_explicit_pre_land_tip_when_current_matches
- tests/test_ticket_land.py::TestVerifiedResetRoot::test_refuses_and_does_not_reset_when_current_tip_has_drifted
- tests/test_ticket_land.py::TestLandRepairMarker::test_no_marker_is_a_silent_no_op
- tests/test_ticket_land.py::TestLandRepairMarker::test_repair_resets_root_when_current_tip_matches_the_marker
- tests/test_ticket_land.py::TestLandRepairMarker::test_repair_recovers_even_when_current_tip_has_drifted_from_the_marker
- tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry
designated_repro_test: null
acceptance:
- text: GIVEN a land killed by SIGTERM mid-staging WHEN the next frob command runs
    THEN main's tip equals the pre-land tip and the repair path reports what was cleaned
  evidence:
  - tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry
- text: GIVEN a land whose failure-unwind runs WHEN main's tip differs from the tip
    recorded at this run's start THEN the unwind refuses loudly instead of resetting
  evidence:
  - tests/test_ticket_land.py::TestVerifiedResetRoot::test_refuses_and_does_not_reset_when_current_tip_has_drifted
evidence_changes:
- old_node: tests/test_ticket_land.py::TestLandRepairMarker::test_repair_refuses_loudly_when_current_tip_has_drifted_from_the_marker
  new_node: tests/test_ticket_land.py::TestLandRepairMarker::test_repair_recovers_even_when_current_tip_has_drifted_from_the_marker
  reason: T-1963 renamed/rewrote this test (refuse-on-drift -> recover-unconditionally,
    since tip drift is the near-guaranteed case under parallel dispatch, not a rare
    edge case) but its own land silently orphaned T-0907's evidence citation rather
    than being refused by _check_orphaned_evidence_deletion (T-1946) as it should
    have been -- floor cleanup only, per the coordinator's own filed ticket for the
    guard defect itself
  actor: logan
  at: '2026-08-10'
threat: tampering
component: tickets
anchor: false
anchor_reason: null
---
Incident 2026-07-23 (this session): two `frob ticket land T-0765` attempts were killed by an external 580s timeout mid-run (SIGTERM, exit 143). Afterward, MAIN's HEAD had been reset from d67a82d2 back to b3589c3e -- the tip from ~60 commits earlier -- with reflog entry "reset: moving to HEAD" transitioning d67a82d2 -> b3589c3e. A subsequent land attempt then refused with the T-0463 IncompleteLand completeness assertion (staged squash-apply missing 5 files), which is what surfaced the damage. Recovery was `git reset --hard d67a82d2` (all objects intact); no data lost, but only because the coordinator checked the reflog before committing anything new.

Root-cause hypotheses to investigate: land records a pre-land tip (or resolves "HEAD") from stale cached state (.frob cache / an earlier killed run's snapshot) and its failure-unwind resets main to that stale value; or the kill mid-staging left HEAD/index in a state where a later unwind's `git reset` resolved HEAD incorrectly. Fix requirements: (1) land's unwind must reset ONLY to the tip it verified at THIS run's start, stored run-locally (not in shared .frob state); (2) the unwind must refuse (loud error, no reset) if main's current tip no longer equals the recorded pre-land tip; (3) signal-safety: land should trap SIGTERM/SIGINT during staging and complete the unwind coherently or leave an explicit .frob/land-in-progress marker that the next invocation repairs; (4) a regression test that SIGKILLs a land mid-staging and asserts main's tip is unchanged afterward.

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
