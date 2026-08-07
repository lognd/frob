---
id: T-1523
title: 'land: checkpoint or split post-land verification so a >540s kill is always
  safe'
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: 'Adding regression tests for the new T-1523 post-land-verify-pending

    marker mechanism.

    '
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_ticket_land.py::TestPostLandVerifyPendingMarker::test_no_marker_is_a_silent_empty_result
- tests/test_ticket_land.py::TestPostLandVerifyPendingMarker::test_stale_marker_reports_verified_true_when_commit_is_a_clean_ancestor
- tests/test_ticket_land.py::TestPostLandVerifyPendingMarker::test_orphaned_marker_from_a_killed_prior_run_is_reported_and_cleared
designated_repro_test: null
threat: null
component: null
---
T-1495 point 4 (filed as a follow-up, not implemented in T-1495 itself):
land duration routinely exceeds the 540s foreground guard (the 2026-08-04
incident's own trigger: `frob ticket land T-1464` was SIGTERM-killed at
that timeout AFTER its land commits were already on main but before
post-land verification finished). Either checkpoint land so a kill is
safe at any instant, or split post-land verification into a resumable
separate step.

This needs a real design decision beyond an unwind-boundary assertion:
- Option A: make every intermediate state durable/self-describing enough
  that a kill at any instant is recoverable by the NEXT invocation
  (T-0907's land-repair marker already does this for the pre-commit
  staging window; the gap is POST-commit, between the final commit
  landing and the post-land unscoped-error sweep / push / worktree
  finish steps -- T-1514 (same cluster, already landed) narrows this
  specific gap by moving T-1456's sweep to run PRE-commit instead of
  post-commit, but push/finish and any other post-commit step are still
  in the killable window).
- Option B: split `frob ticket land` into two separately-invocable
  steps -- "land" (merge/finalize/commit, must complete or cleanly
  unwind) and a separate "land --verify-only <sha>" resumable step that
  re-runs whatever post-land checks remain, safe to kill and retry
  independently of the commit itself ever having happened.

Either option needs its own design doc/ticket-plan before implementation
-- this is exactly the kind of decision the T-1495 body's "find the
actual reset path... make it refuse or reconcile" ask flags as needing
judgment beyond a mechanical fix.