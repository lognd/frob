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
- tests/test_ticket_land.py::TestLandRepairMarker::test_repair_refuses_loudly_when_current_tip_has_drifted_from_the_marker
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
threat: tampering
component: tickets
---
Incident 2026-07-23 (this session): two `frob ticket land T-0765` attempts were killed by an external 580s timeout mid-run (SIGTERM, exit 143). Afterward, MAIN's HEAD had been reset from d67a82d2 back to b3589c3e -- the tip from ~60 commits earlier -- with reflog entry "reset: moving to HEAD" transitioning d67a82d2 -> b3589c3e. A subsequent land attempt then refused with the T-0463 IncompleteLand completeness assertion (staged squash-apply missing 5 files), which is what surfaced the damage. Recovery was `git reset --hard d67a82d2` (all objects intact); no data lost, but only because the coordinator checked the reflog before committing anything new.

Root-cause hypotheses to investigate: land records a pre-land tip (or resolves "HEAD") from stale cached state (.frob cache / an earlier killed run's snapshot) and its failure-unwind resets main to that stale value; or the kill mid-staging left HEAD/index in a state where a later unwind's `git reset` resolved HEAD incorrectly. Fix requirements: (1) land's unwind must reset ONLY to the tip it verified at THIS run's start, stored run-locally (not in shared .frob state); (2) the unwind must refuse (loud error, no reset) if main's current tip no longer equals the recorded pre-land tip; (3) signal-safety: land should trap SIGTERM/SIGINT during staging and complete the unwind coherently or leave an explicit .frob/land-in-progress marker that the next invocation repairs; (4) a regression test that SIGKILLs a land mid-staging and asserts main's tip is unchanged afterward.