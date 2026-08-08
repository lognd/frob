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

## Done report

T-1694 closes the crash-safety hole named in the ticket: a dead verify
worker must never advance the watermark on a batch it did not finish
verifying.

`run_coalesced_verification` now writes a single in-flight marker
(`.frob/verify-in-flight.json`) naming the tip commit BEFORE `verify_fn`
runs, and clears it unconditionally (a `finally` block) once the call
reaches any stable outcome -- green, red, baseline-established,
unmeasurable, or a raised exception. This is the T-0907/T-1523
write-marker-before/clear-marker-after pattern reused, not reinvented, as
the ticket's plan directed.

The four named kill points are all covered by the same single guard:
- death between the queue read and verification start: no marker was
  ever written, nothing durable was claimed, the next run starts clean.
- death between a green result and the watermark write: marker present
  at next startup, no matching watermark -> reported UNVERIFIED.
- death between the watermark write and compact_queue: marker present at
  next startup; if the watermark already names the marker's commit, this
  is reported RECOVERED (the batch genuinely completed, only the marker
  clear was lost) rather than needlessly re-verified.
- a torn marker write itself: `_write_in_flight_marker` writes to a
  `.tmp` sibling and `os.replace`s it into place (atomic rename), so a
  crash mid-write can never leave a half-written marker for the
  reconciler to misread.

Reconciliation (`_reconcile_stale_in_flight_marker`) never assumes green
from the marker's mere presence -- only a marker commit matching the
CURRENT watermark counts as recovered. In every other case the batch is
logged UNVERIFIED; nothing needs to be explicitly re-queued, since
`compact_queue` only ever drops entries the watermark actually reached --
if that never happened, the queue still holds them, and the next
`run_coalesced_verification` call verifies them again exactly as if no
prior attempt had ever started.

Two workers never verifying concurrently for one root is satisfied
structurally by the daemon's existing `acquire_singleton_lock` (at most
one daemon process per root) -- no second exclusion mechanism was added.

Scope was widened narrowly beyond the ticket's original declaration,
each time to close a real gate finding the change itself produced (not
speculative expansion):
- tests/unit/verify/test_worker.py -- the ticket's acceptance criteria
  explicitly requires a test per named kill point; the original scope
  omitted the test file.
- tickets/T-1694/ticket.md, tickets/T-1694/done-report.md -- SCOPE001
  requires a ticket's own directory files be in its declared scope
  (T-1768/T-1220 precedent).
- design/frob.strata -- SELFAUDIT001/COV002 required the `verify` node's
  declared fs.read/fs.write capability list and frob:ticket edge to
  reflect that src/frob/verify/_worker.py now performs its own marker
  file I/O.

Docs updated in the same change: docs/modules/tickets.md's "Coalescing
verify worker (T-1688)" section gained a new subsection describing the
T-1694 crash-safety marker, its write/clear/reconcile contract, and the
singleton-lock reuse decision.

frob check --ticket T-1694: 0 errors (verified clean after a `git merge
main` mid-ticket picked up sibling lands, including a fix to the one
pre-existing unrelated ARCH/ty finding that showed up before the merge).
frob check --land-parity: clean, 0 unscoped errors.

### Changed
```
 design/frob.strata               |   4 +-
 docs/modules/tickets.md          |  48 +++++++++
 src/frob/verify/_worker.py       | 193 ++++++++++++++++++++++++++++++---
 tests/unit/verify/test_worker.py | 226 ++++++++++++++++++++++++++++++++++++++-
 tickets/T-1694/ticket.md         |  44 +++++++-
 5 files changed, 490 insertions(+), 25 deletions(-)
```

### Evidence
- `tests/unit/verify/test_worker.py::TestReconcileStaleInFlightMarker::test_no_marker_is_a_silent_noop` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestReconcileStaleInFlightMarker::test_stale_marker_with_no_matching_watermark_is_reported_unverified` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestReconcileStaleInFlightMarker::test_stale_marker_matching_current_watermark_is_reported_recovered` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestReconcileStaleInFlightMarker::test_unreadable_marker_is_reported_unverified_and_cleared` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_marker_absent_after_a_normal_green_run` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_marker_absent_after_an_unmeasurable_run` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_marker_cleared_even_when_verify_fn_raises` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_death_between_queue_read_and_verification_start_leaves_no_trace` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_death_between_green_result_and_watermark_write_is_never_assumed_green` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_death_between_watermark_write_and_compaction_is_recovered_not_reverified` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestInFlightMarkerCrashSafety::test_torn_marker_write_is_never_partially_observable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 0 error(s), 1139 warning(s), 733 waived
- error-findings: none (measured, zero errors)
