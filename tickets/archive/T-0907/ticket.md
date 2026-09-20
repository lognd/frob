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
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _worker.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1535
  new_length: 2916
evidence:
- tests/ticket_land_suite/test_verify_reset.py::TestVerifiedResetRoot::test_resets_to_the_explicit_pre_land_tip_when_current_matches
- tests/ticket_land_suite/test_verify_reset.py::TestVerifiedResetRoot::test_refuses_and_does_not_reset_when_current_tip_has_drifted
- tests/ticket_land_suite/test_verify_reset.py::TestLandRepairMarker::test_no_marker_is_a_silent_no_op
- tests/ticket_land_suite/test_verify_reset.py::TestLandRepairMarker::test_repair_resets_root_when_current_tip_matches_the_marker
- tests/ticket_land_suite/test_verify_reset.py::TestLandRepairMarker::test_repair_recovers_even_when_current_tip_has_drifted_from_the_marker
- tests/ticket_land_suite/test_verify_reset.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry
designated_repro_test: null
acceptance:
- text: GIVEN a land killed by SIGTERM mid-staging WHEN the next frob command runs
    THEN main's tip equals the pre-land tip and the repair path reports what was cleaned
  evidence:
  - tests/ticket_land_suite/test_verify_reset.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry
- text: GIVEN a land whose failure-unwind runs WHEN main's tip differs from the tip
    recorded at this run's start THEN the unwind refuses loudly instead of resetting
  evidence:
  - tests/ticket_land_suite/test_verify_reset.py::TestVerifiedResetRoot::test_refuses_and_does_not_reset_when_current_tip_has_drifted
evidence_changes:
- old_node: tests/ticket_land_suite/test_verify_reset.py::TestLandRepairMarker::test_repair_refuses_loudly_when_current_tip_has_drifted_from_the_marker
  new_node: tests/ticket_land_suite/test_verify_reset.py::TestLandRepairMarker::test_repair_recovers_even_when_current_tip_has_drifted_from_the_marker
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
land_commit: null
---
Incident 2026-07-23 (this session): two `frob ticket land T-0765` attempts were killed by an external 580s timeout mid-run (SIGTERM, exit 143). Afterward, MAIN's HEAD had been reset from d67a82d2 back to b3589c3e -- the tip from ~60 commits earlier -- with reflog entry "reset: moving to HEAD" transitioning d67a82d2 -> b3589c3e. A subsequent land attempt then refused with the T-0463 IncompleteLand completeness assertion (staged squash-apply missing 5 files), which is what surfaced the damage. Recovery was `git reset --hard d67a82d2` (all objects intact); no data lost, but only because the coordinator checked the reflog before committing anything new.

Root-cause hypotheses to investigate: land records a pre-land tip (or resolves "HEAD") from stale cached state (.frob cache / an earlier killed run's snapshot) and its failure-unwind resets main to that stale value; or the kill mid-staging left HEAD/index in a state where a later unwind's `git reset` resolved HEAD incorrectly. Fix requirements: (1) land's unwind must reset ONLY to the tip it verified at THIS run's start, stored run-locally (not in shared .frob state); (2) the unwind must refuse (loud error, no reset) if main's current tip no longer equals the recorded pre-land tip; (3) signal-safety: land should trap SIGTERM/SIGINT during staging and complete the unwind coherently or leave an explicit .frob/land-in-progress marker that the next invocation repairs; (4) a regression test that SIGKILLs a land mid-staging and asserts main's tip is unchanged afterward.

T-4718 sweep (condensed from src/frob/verify/_worker.py:107-125, trimmed
for DOCARCH002's 12-line cap): the trimmed block's full original text,
kept verbatim below.

# T-1694 incident this closes: a dead worker (killed between the queue
# read and the watermark write, or anywhere in between) must never leave
# main looking verified past a batch that was never actually confirmed
# green. This marker names the batch (its tip commit) and is written
# BEFORE `verify_fn` is even called -- the moment this run starts making a
# claim about `tip.commit_sha` -- and cleared unconditionally once this
# run reaches ANY stable outcome (green, red, baseline-established,
# unmeasurable, or a raised exception), via a `finally` block mirroring
# `_clear_land_repair_marker`'s/`_clear_post_land_verify_marker`'s own
# unconditional-cleanup shape (T-0907/T-1523 precedent). A marker still
# present at the START of the next `run_coalesced_verification` call means
# a prior run died somewhere inside that window -- `_reconcile_stale_
# in_flight_marker` treats that batch as UNVERIFIED unless the watermark
# it finds on disk already independently confirms the same commit (the
# rare case where the crash landed after `advance_watermark`/
# `compact_queue` both actually completed and only the marker clear
# itself was lost) -- it never assumes green from the marker's mere
# presence.