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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: 'Adding regression tests for the new T-1523 post-land-verify-pending

    marker mechanism.

    '
  actor: logan
  at: '2026-08-05'
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _worker.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1671
  new_length: 3052
evidence:
- tests/ticket_land_suite/test_verify_reset.py::TestPostLandVerifyPendingMarker::test_no_marker_is_a_silent_empty_result
- tests/ticket_land_suite/test_verify_reset.py::TestPostLandVerifyPendingMarker::test_stale_marker_reports_verified_true_when_commit_is_a_clean_ancestor
- tests/ticket_land_suite/test_verify_reset.py::TestPostLandVerifyPendingMarker::test_orphaned_marker_from_a_killed_prior_run_is_reported_and_cleared
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
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