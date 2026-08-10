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
