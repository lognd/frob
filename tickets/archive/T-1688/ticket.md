---
id: T-1688
title: 'Coalescing verify worker: drain the queue to its tip, verify once, advance
  the watermark'
state: done
kind: feature
origin: agent
created: '2026-08-06'
priority: critical
blocked_by:
- T-1687
- T-1703
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/verify/_worker.py
- src/frob/serve/_daemon.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets.md
- tests/unit/verify/test_worker.py
- tests/test_serve_daemon.py
- src/frob/verify/__init__.py
- docs/modules/serve.md
- design/frob.strata
- src/frob/verify/_watermark.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/verify/test_worker.py
  reason: unit tests for the new coalescing worker module
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_serve_daemon.py
  reason: tests for the new _poll_verify_worker daemon job
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/verify/__init__.py
  reason: package __init__.py needs its exports updated for the new _worker module
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/serve.md
  reason: AFFECT001 requires the daemon-jobs doc section be touched when _run_daemon_cycle
    changes
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: the new verify design node and testsuite may-list additions live here
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/strata/roadmap.md
  reason: design/frob.strata is whole-file scoped; pre-existing nodes in that file
    (frob, frob.b_vet_endorse, etc) point their frob:doc at this file, so SCOPE002
    requires it in scope too
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: design/frob.strata
  reason: whole-file scope pulled in unrelated pre-existing design nodes' SCOPE002
    doc-target checks; the verify node change is already covered by an explicit frob:ticket
    T-1688 comment, so file-scope isn't needed
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: docs/strata/roadmap.md
  reason: whole-file scope pulled in unrelated pre-existing design nodes' SCOPE002
    doc-target checks; the verify node change is already covered by an explicit frob:ticket
    T-1688 comment, so file-scope isn't needed
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: 'revert: this file is genuinely touched (added node verify); SCOPE001 fires
    without it'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/verify/_watermark.py
  reason: T-1688 wires advance_watermark/compact_queue, resolving their T-1687 WIRE001
    waivers; those waiver deletions live in this file
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_serve_daemon.py::TestFrobDaemonStatus::test_reads_current_status
- tests/test_serve_daemon.py::TestPollPostLand::test_head_moved_refreshes_verdict
- tests/test_serve_daemon.py::TestPollPostLand::test_head_unchanged_is_noop
- tests/test_serve_daemon.py::TestPollRebaseBot::test_clean_branch_no_warning
- tests/test_serve_daemon.py::TestPollRebaseBot::test_conflicting_branch_warns
- tests/test_serve_daemon.py::TestPollRebaseBot::test_no_leases_is_no_warnings
- tests/test_serve_daemon.py::TestPollRebaseBot::test_ttl_expired_lease_skipped_and_logged_once
- tests/test_serve_daemon.py::TestPollRebaseBotLeaseInjectionGuard::test_evil_lease_branch_never_reaches_git_argv
- tests/test_serve_daemon.py::TestPollVerifyWorker::test_head_moved_notifies_the_worker
- tests/test_serve_daemon.py::TestPollVerifyWorker::test_head_unchanged_still_ticks
- tests/test_serve_daemon.py::TestPollVerifyWorker::test_tick_result_is_returned_when_a_run_happens
- tests/test_serve_daemon.py::TestRunDaemonCycle::test_runs_both_jobs_and_returns_status
- tests/test_serve_daemon.py::TestStartDaemon::test_background_loop_runs_a_cycle_then_stops
- tests/unit/test_land_queue.py::TestDrainNext::test_drains_fifo_order
- tests/unit/test_land_queue.py::TestDrainNext::test_empty_queue_returns_none
- tests/unit/test_land_queue.py::TestDrainNext::test_failed_entry_is_not_redrained
- tests/unit/test_land_queue.py::TestDrainNext::test_failed_land_rejected_back_not_retried
- tests/unit/test_land_queue.py::TestDrainNext::test_second_entry_still_drains_after_first_failure
- tests/unit/test_land_queue.py::TestDrainNext::test_successful_land_marks_entry_landed
- tests/unit/test_land_queue.py::TestEnqueue::test_duplicate_enqueue_refused
- tests/unit/test_land_queue.py::TestEnqueue::test_enqueue_after_landed_is_allowed
- tests/unit/test_land_queue.py::TestEnqueue::test_enqueue_persists_across_calls
- tests/unit/test_land_queue.py::TestEnqueue::test_enqueue_returns_queued_entry
- tests/unit/test_land_queue.py::TestFileLock::test_creates_the_lock_file
- tests/unit/test_land_queue.py::TestFileLock::test_serializes_a_read_modify_write_sequence
- tests/unit/test_land_queue.py::TestQueueStatus::test_empty_queue_is_empty_tuple
- tests/unit/test_land_queue.py::TestStoreCorrupt::test_corrupt_queue_file_errors
- tests/unit/test_land_queue.py::TestWriteJsonRecords::test_round_trips_via_load_queue
- tests/unit/test_land_queue.py::TestWriteJsonRecords::test_writes_a_json_array
- tests/unit/verify/test_watermark.py::TestAdvanceWatermark::test_advance_overwrites_prior_watermark
- tests/unit/verify/test_watermark.py::TestAdvanceWatermark::test_advance_then_load_round_trips
- tests/unit/verify/test_watermark.py::TestCompactQueue::test_drops_entries_at_or_before_watermark
- tests/unit/verify/test_watermark.py::TestCompactQueue::test_keeps_entries_after_watermark
- tests/unit/verify/test_watermark.py::TestCompactQueue::test_no_watermark_yet_is_a_noop
- tests/unit/verify/test_watermark.py::TestCompactQueue::test_watermark_commit_absent_from_queue_is_a_noop
- tests/unit/verify/test_watermark.py::TestLoadWatermark::test_corrupt_file_reads_as_none_not_verified
- tests/unit/verify/test_watermark.py::TestLoadWatermark::test_missing_file_is_none
- tests/unit/verify/test_watermark.py::TestLoadWatermark::test_round_trips
- tests/unit/verify/test_watermark.py::TestQueueStatus::test_corrupt_queue_errors
- tests/unit/verify/test_watermark.py::TestQueueStatus::test_empty_queue_is_empty_tuple
- tests/unit/verify/test_watermark.py::TestRecordIntent::test_appends_one_entry_with_resolvable_symbols
- tests/unit/verify/test_watermark.py::TestRecordIntent::test_corrupt_queue_refuses_to_append
- tests/unit/verify/test_watermark.py::TestRecordIntent::test_empty_touched_symbols_refused
- tests/unit/verify/test_watermark.py::TestRecordIntent::test_persists_across_calls_in_order
- tests/unit/verify/test_worker.py::TestCoalescingWorker::test_notify_then_tick_after_deadline_runs_once
- tests/unit/verify/test_worker.py::TestCoalescingWorker::test_notify_then_tick_before_deadline_does_not_run
- tests/unit/verify/test_worker.py::TestCoalescingWorker::test_periodic_floor_forces_a_run_under_continuous_notify
- tests/unit/verify/test_worker.py::TestCoalescingWorker::test_repeated_notify_pushes_the_deadline_out
- tests/unit/verify/test_worker.py::TestCoalescingWorker::test_tick_with_nothing_pending_is_a_noop
- tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_clean_run_advances_watermark_and_compacts_queue
- tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_empty_queue_is_a_noop
- tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_first_run_establishes_baseline_without_advancing
- tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_five_queued_entries_call_verify_exactly_once
- tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_new_findings_file_a_ticket_and_do_not_advance
- tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_queue_unreadable_is_an_error
- tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_unmeasurable_never_advances_watermark
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
---
The trailing-edge-debounce half of the epic, and where the wall-clock
saving actually comes from.

The worker must COALESCE, not iterate. On wake: read the queue, take its
TIP commit, verify once at that tip, and on green advance the watermark
past every entry at or below it. A FIFO worker that verifies each entry
in turn reproduces exactly the per-land cost this epic exists to remove
-- if the implementation ever loops over entries running a check per
entry, it has missed the point.

Verification at the tip is what makes this sound: tree state is the only
input, so a green result at the tip is a green result for every commit
that composes it. What it does NOT give you is per-commit attribution --
that is deliberately deferred to the attribution leaf, and this leaf must
not pretend to answer it.

Wake conditions: a queue append, the FS-watch signal `frob.serve._watch`
already provides, and a periodic floor so a stalled watcher cannot leave
the window open indefinitely. Debounce so a burst of five lands in ninety
seconds produces one verification, not five.

T-1684's `sweep-async` becomes this worker's body rather than a
per-land spawn. Keep the rolling baseline; it is already the right
comparison substrate.

Acceptance: five lands inside the debounce window produce exactly ONE
full verification pass and one watermark advance covering all five,
demonstrated by a test that counts verification invocations rather than
by inspecting timings.

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