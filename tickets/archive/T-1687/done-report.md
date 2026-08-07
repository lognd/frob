## Done report

Built the T-1687 foundation of the T-1686 verification-watermark epic:
a new frob.verify package (src/frob/verify/_watermark.py) with two
persisted pydantic records and their read/write primitives, and nothing
else -- no daemon, no worker, no CLI wiring, per the ticket's own "the
foundation, not the worker" framing.

- VerifyQueueEntry: append-only intent log, one per land. commit_sha,
  ticket_id, touched_symbols (a tuple of symref-shaped SYMBOL ids --
  never file paths), enqueued_at, profile.
- Watermark: single record, "main is verified through commit_sha, at
  verified_at, by run_id, against baseline_digest".
- record_intent/queue_status for the queue; load_watermark/
  advance_watermark for the watermark; compact_queue drops entries at-
  or-before the current watermark (the ONE operation that shortens the
  file -- record_intent only ever appends).

TOUCHED SYMBOLS, NOT FILE PATHS (the one thing the coordinator flagged
as easy to miss and impossible to retrofit): VerifyQueueEntry.
touched_symbols is a tuple of symref-shaped ids, matching what
frob.graph.GraphSnapshot.symbols keys on -- never a path list. Computing
that set from a real Diff/GraphSnapshot is deliberately OUT of this
module's own scope (frob.verify never imports frob.graph, keeping the
cycle-avoidance rule docs/rework.md already establishes for
frob.tickets); a caller with graph access resolves and passes the set
in. record_intent refuses outright on an empty touched_symbols tuple --
a land with nothing for tier-2 attribution to reach would otherwise make
every later finding at that commit permanently unattributable.

"Cannot verify" is never "verified": load_watermark treats a missing
watermark file and a CORRUPT one identically -- both return Ok(None),
logged at WARNING in the corrupt case so the corruption stays visible
even though the read degrades safely. queue_status, by contrast,
propagates a corrupt QUEUE file as Err rather than degrading to empty --
an unreadable intent log misread as "nothing pending" is itself a false
"how far is main verified" claim.

Reused, not reinvented: extracted frob.tickets._land_queue's fcntl lock
into a shared, `label`-tagged file_lock context manager (both the merge
queue's own _queue_lock and both of frob.verify's locks now call it) so
this repo does not end up with three near-identical fcntl
implementations for one class of problem. Caught during my own land-
parity re-check (not by a reviewer) that my first draft ALSO duplicated
_land_queue._save_queue's JSON-array write body byte-for-byte (DUP001
flagged it directly, 100% similar) -- extracted a second shared helper,
write_json_records, and pointed both call sites at it.

design/frob.strata: added a new `verify` node bound to src/frob/verify/**
(clearance Internal, may fs.read/fs.write via _watermark.py), and ran
`frob sys sync-interface` to populate the measured interface= lists on
both the new node and tickets_ledger (file_lock/write_json_records are
now cross-node-referenced by frob.verify, per SYS104's mandatory-since-
T-1113 check).

Waivers, each naming the real reason rather than suppressing blind:
- INV006 (split-carried-prose preset) on the new module's own docstring
  ("append-only" trips the bare \bonly\b heuristic).
- TEST003 on frob.verify (0 integration tests) -- unit-tested
  exhaustively; no CLI/subprocess entrypoint exists yet by design.
- WIRE001 x3 (record_intent/advance_watermark/compact_queue) -- each
  follow_up="T-1688", the already-filed, open coalescing-worker ticket
  that is the real land()-time/drainer caller this foundation ticket
  deliberately does not wire in itself.

Verified with:
- pytest across both touched test files -- 31 passed
  (tests/unit/verify/test_watermark.py: 15, tests/unit/test_land_queue.py:
  16, the latter now also covering file_lock and write_json_records
  directly).
- ruff check / ruff format --check -- clean.
- ty check -- clean.
- `frob check --only sys --ticket T-1687` -- 0 errors (SELFAUDIT001/
  SYS104 clean after the design-node addition + sync-interface).
- `frob check --only coverage --only sys --only test --only clones
  --only invariant --only wire --ticket T-1687` -- 0 errors on every file
  this ticket touches; DUP001/INV006/WIRE001 all resolved.
- `frob check --land-parity` -- 4 remaining unscoped errors, all
  verified pre-existing and unrelated (ARCH001 in
  src/frob/tickets/_evidence.py, COV003 stale evidence on the archived
  T-1637, DOC009 on docs/audits/docs-completeness-2026-08-06.md, a ty
  finding in tests/test_ticket_work_and_land_finish.py) -- none touch a
  file this ticket's scope covers; confirmed via `git log` that each was
  last modified by an unrelated ticket that landed via main while this
  one was in flight.

### Changed
```
 .frob-release.json                  |   4 +-
 CHANGELOG.md                        |   4 -
 design/frob.strata                  |  54 +++--
 docs/modules/tickets.md             | 101 +++++++++
 pyproject.toml                      |   2 +-
 src/frob/tickets/_land_queue.py     |  93 +++++---
 src/frob/verify/__init__.py         |  39 ++++
 src/frob/verify/_watermark.py       | 422 ++++++++++++++++++++++++++++++++++++
 tests/unit/test_land_queue.py       |  46 ++++
 tests/unit/verify/__init__.py       |   0
 tests/unit/verify/test_watermark.py | 257 ++++++++++++++++++++++
 tickets.md                          |  39 +++-
 uv.lock                             |   2 +-
 13 files changed, 1005 insertions(+), 58 deletions(-)
```

### Evidence
- `tests/unit/verify/test_watermark.py::TestQueueStatus::test_empty_queue_is_empty_tuple` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_watermark.py::TestQueueStatus::test_corrupt_queue_errors` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_watermark.py::TestRecordIntent::test_appends_one_entry_with_resolvable_symbols` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_watermark.py::TestRecordIntent::test_empty_touched_symbols_refused` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_watermark.py::TestRecordIntent::test_corrupt_queue_refuses_to_append` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_watermark.py::TestLoadWatermark::test_missing_file_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_watermark.py::TestLoadWatermark::test_round_trips` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_watermark.py::TestLoadWatermark::test_corrupt_file_reads_as_none_not_verified` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_watermark.py::TestAdvanceWatermark::test_advance_then_load_round_trips` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_watermark.py::TestCompactQueue::test_drops_entries_at_or_before_watermark` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_watermark.py::TestCompactQueue::test_watermark_commit_absent_from_queue_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_watermark.py::TestCompactQueue::test_no_watermark_yet_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestFileLock::test_serializes_a_read_modify_write_sequence` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestWriteJsonRecords::test_round_trips_via_load_queue` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestWriteJsonRecords::test_writes_a_json_array` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: 5 error(s), 409 warning(s), 722 waived
- error-findings: ARCH001@src/frob/tickets/_evidence.py, COV003@tickets/T-1637, DOC009@docs/audits/docs-completeness-2026-08-06.md, PRE001@tickets/T-1687, unresolved-attribute@tests/test_ticket_work_and_land_finish.py
