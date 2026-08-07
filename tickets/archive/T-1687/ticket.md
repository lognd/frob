---
id: T-1687
title: 'Verification watermark: durable commit-keyed verify queue and verified-through
  record'
state: done
kind: feature
origin: agent
created: '2026-08-06'
priority: critical
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/verify/_watermark.py
- src/frob/tickets/_land_queue.py
- docs/modules/tickets.md
- src/frob/verify/__init__.py
- tests/unit/verify/test_watermark.py
- tests/unit/test_land_queue.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/verify/__init__.py
  reason: a new package needs an __init__.py to be importable at all; same directory
    as the declared _watermark.py module
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/verify/test_watermark.py
  reason: test coverage for the new module and the file_lock extraction in _land_queue.py
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_land_queue.py
  reason: test coverage for the new module and the file_lock extraction in _land_queue.py
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/verify/test_watermark.py::TestQueueStatus::test_empty_queue_is_empty_tuple
- tests/unit/verify/test_watermark.py::TestQueueStatus::test_corrupt_queue_errors
- tests/unit/verify/test_watermark.py::TestRecordIntent::test_appends_one_entry_with_resolvable_symbols
- tests/unit/verify/test_watermark.py::TestRecordIntent::test_empty_touched_symbols_refused
- tests/unit/verify/test_watermark.py::TestRecordIntent::test_corrupt_queue_refuses_to_append
- tests/unit/verify/test_watermark.py::TestLoadWatermark::test_missing_file_is_none
- tests/unit/verify/test_watermark.py::TestLoadWatermark::test_round_trips
- tests/unit/verify/test_watermark.py::TestLoadWatermark::test_corrupt_file_reads_as_none_not_verified
- tests/unit/verify/test_watermark.py::TestAdvanceWatermark::test_advance_then_load_round_trips
- tests/unit/verify/test_watermark.py::TestCompactQueue::test_drops_entries_at_or_before_watermark
- tests/unit/verify/test_watermark.py::TestCompactQueue::test_watermark_commit_absent_from_queue_is_a_noop
- tests/unit/verify/test_watermark.py::TestCompactQueue::test_no_watermark_yet_is_a_noop
- tests/unit/test_land_queue.py::TestFileLock::test_serializes_a_read_modify_write_sequence
- tests/unit/test_land_queue.py::TestWriteJsonRecords::test_round_trips_via_load_queue
- tests/unit/test_land_queue.py::TestWriteJsonRecords::test_writes_a_json_array
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
---
The foundation every other leaf depends on. Useless alone; land it first
anyway, because retrofitting a durable record under a running worker is
strictly harder than building on one.

Two persisted records:

1. VERIFY QUEUE -- append-only intent log. One entry per land: commit
   sha, ticket id, the TOUCHED SYMBOL SET (symbol ids from the graph, NOT
   file paths -- tier-2 attribution is impossible without this, and a
   path list is the lexical shortcut that makes it wrong under refactor),
   enqueue timestamp, and the profile in force. Written BEFORE the land
   returns, in the same spirit as T-1684's record_rapid_debt: an
   unverified commit must never be a silent one, even if every consumer
   dies immediately after.
2. WATERMARK -- "verified through commit X at time T, by run R, against
   baseline B". Advances only on a fully green batch verification.

Both are pydantic models, frozen, extra-forbidding, schema-versioned.
The queue is append-only with compaction below the watermark, never
rewritten in place -- a torn rewrite of a shared intent log is exactly
the corruption class this epic exists to avoid.

Reuse `_land_queue`'s existing lock discipline rather than inventing a
second locking protocol; two lock protocols over adjacent state in one
repo is a deadlock waiting to be discovered in production.

Acceptance: a land appends exactly one queue entry with a resolvable
symbol set; the watermark round-trips; a truncated/corrupt queue file
reads as "nothing verified" (never as "all verified") and says so at
WARNING.

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