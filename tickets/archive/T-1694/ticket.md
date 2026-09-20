---
id: T-1694
title: 'Crash safety: a dead verify worker must never advance the watermark'
state: done
kind: bug
origin: agent
created: '2026-08-06'
priority: high
blocked_by:
- T-1688
parent: T-1686
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/verify/_worker.py
- src/frob/tickets/_land.py
- docs/modules/tickets.md
- tests/unit/verify/test_worker.py
- tickets/T-1694/ticket.md
- tickets/T-1694/done-report.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/verify/test_worker.py
  reason: T-1694's own acceptance requires kill-point tests per named crash window;
    the declared scope omitted the test file the ticket itself demands
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1694/ticket.md
  reason: SCOPE001 requires the ticket's own directory files be in its declared scope,
    matching the established T-1768/T-1220 precedent
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1694/done-report.md
  reason: SCOPE001 requires the ticket's own directory files be in its declared scope,
    matching the established T-1768/T-1220 precedent
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001 requires the verify node's declared fs.read/fs.write capability
    list in design/frob.strata to include src/frob/verify/_worker.py now that it performs
    its own marker file I/O
  actor: logan
  at: '2026-08-08'
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _worker.py'
  actor: logan
  at: '2026-09-19'
  old_length: 2442
  new_length: 3823
evidence:
- tests/unit/verify/test_worker.py::TestReconcileStaleInFlightMarker::test_no_marker_is_a_silent_noop
- tests/unit/verify/test_worker.py::TestReconcileStaleInFlightMarker::test_stale_marker_with_no_matching_watermark_is_reported_unverified
- tests/unit/verify/test_worker.py::TestReconcileStaleInFlightMarker::test_stale_marker_matching_current_watermark_is_reported_recovered
- tests/unit/verify/test_worker.py::TestReconcileStaleInFlightMarker::test_unreadable_marker_is_reported_unverified_and_cleared
- tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_marker_absent_after_a_normal_green_run
- tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_marker_absent_after_an_unmeasurable_run
- tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_marker_cleared_even_when_verify_fn_raises
- tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_death_between_queue_read_and_verification_start_leaves_no_trace
- tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_death_between_green_result_and_watermark_write_is_never_assumed_green
- tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_death_between_watermark_write_and_compaction_is_recovered_not_reverified
- tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_torn_marker_write_is_never_partially_observable
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
anchor: false
anchor_reason: null
land_commit: null
---
The watermark is a claim that work was done. Every way it can advance
without that work having been done is a correctness hole, and they are
all crash-shaped.

Reuse the T-1523 post-land-verify marker pattern rather than inventing a
second one: write an in-flight marker naming the batch and target commit
before verification begins, clear it after the watermark advances. A
marker found at startup means a worker died mid-verification; that batch
is UNVERIFIED and must be re-queued, never assumed green.

Specific holes to close, each with a test that kills the worker at that
exact point: death between queue read and verification start; between a
green result and the watermark write; between the watermark write and
queue compaction; and a torn watermark write (write-temp-then-rename, so
a partial file is never observable).

Two workers must never verify concurrently for one root -- reuse the
daemon's existing singleton lock, do not add a second exclusion
mechanism.

Acceptance: for each named kill point, the next startup reports the batch
as unverified and re-queues it; the watermark never names a commit whose
verification did not complete.

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.

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