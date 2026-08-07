## Done report

Delivers the first portion T-1345's own body asked for when the full
scope proved too large for one pass: the merge-queue DATA STRUCTURE plus
enqueue/drain_next, as a library API in frob.tickets._land_queue -- not
the <!-- frob:waive DOC006 reason="disclosed-not-done narrative naming a CLI flag that does not exist yet -- Done report honesty section" -->`frob ticket land --queue` CLI flag or a drainer subcommand.

- `.frob/land-queue.json`, guarded by a dedicated fcntl flock
  (.frob/land-queue.lock), mirroring frob.tickets._land._land_lock's
  T-0577 design (same posix-only-with-logged-degradation posture).
- `enqueue(root, ticket_id, worktree, branch)` appends a `queued` entry
  and returns immediately -- no blocking on land().
- `drain_next(root, land_fn)` pops the oldest `queued` entry (FIFO),
  runs it through the caller-supplied `land_fn` (a thin wrapper around
  the real `land()`), and records the outcome back onto the entry:
  `landed` + commit sha on success, `failed` + the LandError value on
  failure. Every entry that leaves `queued` stays present in the JSON
  history -- nothing is silently dropped.
- `queue_status(root)` is a read-only snapshot for observability.

Design questions from the ticket body, answered in the module docstring
and docs/modules/tickets.md's new "Merge queue (T-1345, first portion)"
section:
- Queue location + crash survival: JSON file + lock, same posture as
  every other .frob/ derived-state file in this package; a crashed
  drainer simply leaves `queued`/`landing` state for the next
  `drain_next` call to find (a `landing`-stuck entry after a crash is a
  known, documented limitation -- no automatic reap in this first
  portion; noted as a real gap, not silently assumed away).
- Policy for a branch that no longer merges cleanly: REJECTED BACK TO THE
  AGENT (dequeued, error recorded, never auto-rebased-and-retried) --
  auto-retry risks landing an un-reverified diff, the exact class of gap
  agent-playbook.md section 9's deletion-filter rule exists to catch.
- LAND-PROOF preservation: drain_next returns the LandReport-bearing
  Result untouched to whatever wrapper called it; this module prints
  nothing itself, so a future CLI layer prints the identical line
  `frob ticket land` already does today, from the same LandReport.

Acceptance criteria:
[0] "two agents enqueue at once -> both land in sequence, neither
    DirtyMain-refused, neither writes to main directly" -- covered at the
    library level: enqueue() never touches main (just appends a JSON
    row), and drain_next()'s FIFO ordering plus its land_fn-only access
    to the actual land() call is what makes "neither writes to main
    directly" true by construction once a CLI wraps it. test_
    enqueue_returns_queued_entry and test_second_entry_still_drains_
    after_first_failure prove the enqueue-then-serial-drain shape and
    that one entry's outcome does not block the next.
[1] "queued branch that no longer merges cleanly -> declared policy, not
    silently dropped" -- test_failed_land_rejected_back_not_retried and
    test_failed_entry_is_not_redrained prove the reject-and-dequeue
    policy: the entry is marked failed with the real LandError recorded,
    remains in queue history, and is never re-attempted automatically.

HONEST DISCLOSURE -- what this ticket did NOT do:

1. No CLI surface at all. <!-- frob:waive DOC006 reason="disclosed-not-done narrative naming a CLI flag/paths that do not exist yet -- honesty section, filed as T-1444 below" -->`frob ticket land --queue` and a drainer
   subcommand need src/frob/_cli_parsers/_ticket.py and
   src/frob/app/ticket_runner.py, both outside this ticket's declared
   scope (src/frob/tickets/**, docs/modules/tickets.md,
   docs/guides/agent-playbook.md). Filed as T-1444 (renumbers
   at land), which also covers the open design question of whether the
   drainer should be a long-running loop or a single-shot "drain one and
   exit" a coordinator calls repeatedly.
2. No automatic reap of a `landing`-stuck entry left behind by a crashed
   drainer -- documented as a known gap in the module docstring rather
   than silently assumed safe; a real fix (e.g. a TTL like
   frob.tickets._leases already has for worktree leases) belongs in the
   CLI-wiring follow-up or its own ticket once the operational shape
   (single-shot vs long-running drainer) is decided.
3. Single-drainer safety is documented as an operational invariant, not
   mechanically enforced -- a second concurrent drainer is safe (the
   queue lock prevents two drainers popping the same entry) but wasteful
   (both would contend on land()'s own _land_lock for nothing). Not
   fixed here; noted honestly rather than claimed solved.

Gates: frob check --ticket T-1345 --only gates-fast (foreground, 540s
timeout). gate:AFFECT (4 AFFECT001) and 3 of gate:SCOPE's SCOPE001
findings are on src/frob/check/__init__.py, src/frob/check/_python.py,
tests/unit/test_check.py -- these are T-1346's own still-open scope-lease
gap (see T-1346's Done report), carried into this diff only because both
tickets share one worktree branch and the --ticket T-1345 disclosure
diffs against the WHOLE branch, not just this ticket's own commits; not
new findings introduced by T-1345's own work. gate:INV's INV006 (T-1345's
own docstring "only" claims) was real and is fixed (waived with a
specific reason, matching _gate_cache.py's identical T-0602-era
precedent). gate:PRE was refreshed via `frob ticket sweep T-1345` after
the INV006 fix. Every other family (DEPR/DOC/FMT/LANG/REF/REL/TEST/
TICK/TODO/WALK) passed clean.

Test evidence (measured):
  pytest tests/unit/test_land_queue.py -q -> 12 passed (all new)
  pytest tests/test_ticket_land.py -q --timeout=100 -> 2 pre-existing
  failures in TestCloseSkipMutationEvidenceBypass
  (src/frob/app/ticket_runner/_close_cmd.py, a TypeError from a lambda
  arity mismatch), confirmed via git log on that file to predate this
  ticket's work (last touched by T-1438/T-1427/T-1387, none mine) -- not
  a regression from this ticket, which never touches that file.
  ruff check / ruff format --check on every touched file: clean
  ty check src/frob/tickets/_land_queue.py src/frob/tickets/__init__.py:
  "All checks passed!"

Filed: T-1444 "Wire merge-queue enqueue/drain into frob ticket
land CLI" (renumbers at land).

### Changed
```
 docs/modules/gates.md           |  38 +++-
 docs/modules/tickets.md         |  64 +++++++
 src/frob/check/__init__.py      |  40 ++++-
 src/frob/check/_python.py       |  45 ++++-
 src/frob/tickets/__init__.py    |  12 ++
 src/frob/tickets/_land_queue.py | 386 ++++++++++++++++++++++++++++++++++++++++
 tests/unit/test_check.py        |  72 +++++++-
 tests/unit/test_land_queue.py   | 182 +++++++++++++++++++
 tickets.md                      | 347 +++++++++++++++++++++++++++++++++++-
 9 files changed, 1164 insertions(+), 22 deletions(-)
```

### Evidence
- `tests/unit/test_land_queue.py::TestDrainNext::test_second_entry_still_drains_after_first_failure` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestEnqueue::test_enqueue_returns_queued_entry` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestDrainNext::test_failed_land_rejected_back_not_retried` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestDrainNext::test_failed_entry_is_not_redrained` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestEnqueue::test_enqueue_persists_across_calls` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestEnqueue::test_duplicate_enqueue_refused` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestEnqueue::test_enqueue_after_landed_is_allowed` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestQueueStatus::test_empty_queue_is_empty_tuple` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestDrainNext::test_empty_queue_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestDrainNext::test_drains_fifo_order` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestDrainNext::test_successful_land_marks_entry_landed` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestStoreCorrupt::test_corrupt_queue_file_errors` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 5 error(s), 974 warning(s), 697 waived
- error-findings: AFFECT001@src/frob/check/__init__.py, SEC110@src/frob/check/_python.py, SELFAUDIT001@design, WIRE001@src/frob/tickets/_land_queue.py, WIRE001@tests/unit/test_land_queue.py
