---
id: T-3328
title: TestArchive's 5 baseline failures are git worktree list exit 128 under load
  hitting T-3230's new fail-closed path
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_archive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TWO INDEPENDENT OBSERVATIONS OF THE SAME FIVE TESTS, connected here.

1. Series DS's full chunked baseline of main listed these five in cluster J as
   UNCHARACTERIZED, with no shared root cause found:

       tests/test_tickets.py::TestArchive::test_idempotent_second_run_moves_nothing
       tests/test_tickets.py::TestArchive::test_moves_done_and_dropped_only
       tests/test_tickets.py::TestArchive::test_load_queue_merges_active_and_archive
       tests/test_tickets.py::TestArchive::test_new_ticket_id_continues_past_archived_max
       tests/test_tickets.py::TestArchive::test_blocked_by_archived_ticket_resolves_closed

2. Series DX, working an unrelated ticket, independently observed the same five
   failing on `git worktree list` EXIT 128 under heavy host load, and noted it
   reproduced only under contention, not deterministically. It correctly
   declined to file on an unconfirmed premise.

Same five tests, same file, two agents, two routes. That is enough to stop
calling them uncharacterized.

HYPOTHESIS -- NOT VERIFIED, AND THE INTERESTING PART IS THAT IT IMPLICATES A
FIX RATHER THAN A BUG. T-3230 (landed 27bd2c0bcce3) deliberately changed
archive's live-worktree measurement to FAIL CLOSED. `src/frob/tickets/
_archive.py:276` now returns `TicketError.ArchiveWorktreeMeasurementFailed`
when the worktree list cannot be measured, where the pre-fix code fell through
into silently permitting the archive.

That change is CORRECT and must not be reverted -- an unmeasurable worktree
list previously read as "no live worktrees", which is the silent-zero class and
exactly what T-3230 was filed to kill.

But it means a `git worktree list` that fails under load now produces a REFUSAL
where it previously produced a silent pass. If these tests were passing before
T-3230 by accident -- because the failed measurement degraded to "empty" and
archive proceeded -- then T-3230 converted a latent, invisible defect into five
visible test failures. That is the fix working as designed, and the tests are
now telling the truth about a fragile measurement.

WHAT TO DETERMINE, in this order:
  1. Do these five fail because of the T-3230 refusal path? Check whether the
     failure message names `ArchiveWorktreeMeasurementFailed` or the live-
     worktree refusal, versus failing some other way. If it is neither, this
     whole hypothesis is wrong -- say so and re-triage from the actual error.
  2. Did they pass before T-3230? Check out its parent and run them under the
     same contention. If they passed only because the measurement silently
     degraded, record that plainly -- it is the strongest possible evidence
     that T-3230 was worth doing.
  3. WHY does `git worktree list` exit 128 under load at all? That is the real
     defect underneath. Contention on the git index or worktree metadata is a
     transient, expected condition on a box running several agent fleets; a
     transient git failure should be retried or reported as transient, not
     treated as a permanent unmeasurable state.

DO NOT FIX THIS BY MAKING ARCHIVE FAIL OPEN AGAIN, and do not fix it by marking
the tests flaky or adding a retry decorator to them. Both delete the detector.
If the measurement is genuinely transient, the retry belongs in the MEASUREMENT
(bounded, logged per attempt), not in the test.

SIBLING SURFACE TO CHECK AND REPORT, NOT FIX: T-3230 triaged 37 `git`-spawn
call sites and judged 28 "low-stakes/advisory where the empty-on-failure
direction is already safe". This incident is evidence that at least one such
judgement deserves re-examination under real contention. Report how many of
those 28 sit on a path that can refuse or mutate state; do not re-open them all.

MUST-FIRE FIXTURE: an archive attempt whose `git worktree list` fails is
refused with the unmeasurable error, distinct from a genuine live-worktree
refusal.
MUST-STAY-QUIET FIXTURE: a normal archive in a quiet tree still succeeds, and
the five named tests pass under ordinary conditions.
THIRD FIXTURE: a transient measurement failure that succeeds on retry does not
surface as a refusal at all.

ACCEPTANCE
- A stated answer to (1) and (2) with evidence.
- The transient-versus-permanent distinction made in the measurement, not in
  the tests.
- The five named tests pass under contention, without being marked flaky.
- A stated count for the sibling surface.
