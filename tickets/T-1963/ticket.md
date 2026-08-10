---
id: T-1963
title: Land serializes on a repo-wide lock, so at 5-agent dispatch the queue wait
  exceeds the 540s guard and killed lands leave the shared root dirty
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: T-1963's fix changes _reconcile_one_land_repair_marker's tip-drifted behavior
    from refuse to repair; the existing TestLandRepairMarker regression test in this
    file must be updated to match, plus a new drift-recovery test
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_land.py::TestLandRepairMarker::test_repair_recovers_even_when_current_tip_has_drifted_from_the_marker
- tests/test_ticket_land.py::TestLandRepairMarker::test_repair_resets_root_when_current_tip_matches_the_marker
- tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry
designated_repro_test: tests/test_ticket_land.py::TestLandRepairMarker::test_repair_recovers_even_when_current_tip_has_drifted_from_the_marker
threat: null
component: null
anchor: false
anchor_reason: null
---
`frob ticket land` serializes on a repo-wide lock. At the standing
dispatch target (5 agents in parallel), the queue wait alone exceeds the
540s timeout guard the project's own hook mandates -- so lands are killed
mid-staging, leaving a land-repair marker and a dirty shared root, which
blocks EVERY other agent until a coordinator recovers it by hand.

MEASURED, 2026-08-10, twice within 20 minutes on T-1809:
  attempt 1: `timeout 540 uv run frob ticket land T-1809 --worktree ...`
             -> exit 143 (SIGTERM), land-repair marker T-1809.json
             written, 6 files left staged in the shared root, ticket
             marked done in the WORKING TREE while main's committed
             ledger still read `queued`.
  attempt 2: identical command, identical exit 143.
  At the moment of attempt 2: `pgrep -f 'frob ticket land T-' | wc -l`
  reported 6 concurrent land processes.

The same shape hit two agents independently in the same window: the
strata-dedup agent had three failed land attempts (one SIGTERM
mid-staging plus two DirtyMain refusals) and stopped; the config-sync
agent could not land T-1809 at all and correctly refused to recover the
root itself.

WHY IT COMPOUNDS: a killed land does not just fail, it leaves damage.
Recovery is not automatic -- `_reconcile_one_land_repair_marker` REFUSES
when main's tip has moved since the recorded pre-land tip (correctly: its
repair is `git reset --hard <recorded_tip>`, which would destroy any
commit landed in between). Under parallel dispatch main's tip moves
constantly, so the automatic path is exactly the path that cannot run,
and every crash needs a human. Manual recovery is also sharp: `git clean
-fd`, which the error text suggests, would have deleted a freshly-filed
untracked ticket directory (T-1962) sitting in the root during this
session's recovery.

DO NOT FIX IT THIS WAY:
- Do NOT just raise the timeout. That trades a fast failure for a slow
  one and still fails at higher agent counts; the queue is unbounded.
- Do NOT remove the land lock. Concurrent ledger writes during a land
  corrupt the ledger, which has taken every gate down here before.
- Do NOT make the timeout guard advisory. It exists because
  auto-backgrounded frob commands are a known stall pattern.

FIX DIRECTION, preferred order:
(a) Make the staging window CRASH-SAFE so a killed land leaves the
    shared root untouched -- stage into a temp index/worktree and make
    the root mutation a single atomic step. Then a SIGTERM costs a
    retry, not a coordinator recovery.
(b) Have land WAIT for the lock explicitly with visible queue position
    ("waiting behind N lands"), so the caller can see contention rather
    than inferring it from a timeout.
(c) Make `_reconcile_one_land_repair_marker` able to repair a
    tip-moved root by resetting only the paths the crashed land staged,
    instead of refusing wholesale.

ACCEPTANCE: first test must FAIL before the fix -- SIGTERM a land
mid-staging and assert the shared root is left clean with no marker.
Then assert a land that is killed while N other lands are queued still
leaves the root landable by another agent without manual intervention.