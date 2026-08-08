## Done report

Added the T-1845 land-finish-pending marker to
src/frob/app/ticket_runner/_land_cmd.py, mirroring T-1523's post-land-
verify-pending marker shape one-for-one:

- _land_finish_pending_dir / _land_finish_pending_marker_path: the
  <root>/.frob/land-finish-pending/<ticket_id>.json path.
- _write_land_finish_pending_marker / _clear_land_finish_pending_marker:
  best-effort write/clear, logged-not-raised on an OSError.
- _stale_land_finish_pending_markers: read-only scan of leftover markers.
- _report_stale_land_finish_pending_markers: reconciles (logs a
  LAND-FINISH-RECOVERED line, clears) every leftover marker -- wired into
  _land_core right alongside its T-1523 sibling
  _report_stale_post_land_verify_markers, at the very start of the next
  `frob ticket land` invocation.
- _finish_land_after_success now writes the marker immediately before
  _finish_worktree runs (the two mutations: git worktree remove, and
  --retire-on-proof's additional git branch -D) and clears it in a
  `finally` block once both attempted mutations return -- covering the
  exact unmarked SIGTERM window T-1554's design doc audit named.

Evidence: 5 tests in tests/unit/test_land_finish_guard.py -- a plain
write/clear/reconcile round trip (TestLandFinishPendingMarker, 4 tests)
plus a load-bearing real-process SIGTERM-injection test
(TestLandFinishPendingMarkerSigterm), matching T-0907's own SIGKILL-mid-
squash precedent shape: a forked child writes the marker, then (via a
monkeypatched _finish_worktree) signals readiness and sleeps; the parent
sends a real SIGTERM once ready, then asserts the marker survived the
kill and that the next reconciliation pass finds, reports, and clears it.
Not a unit-level mock -- a real process is killed mid-mutation.

Fixed two false-positive gate findings surfaced while getting T-1845
clean: a PERF001/PERF003 pair the perf scanner tripped on a caplog-
records list-comprehension-then-index pattern (rewritten as a shared
_sole_matching_log_message test helper using an explicit for loop
instead), and two WIRE001 findings on the new test-only helpers
(_sole_matching_log_message, _t1845_child_finish) -- both waived
permanent="true", matching this same file's own pre-existing
_add_worktree/_make_design_worktree precedent for a helper with
deliberately no production caller.

### Changed
```
 tickets/T-1845/ticket.md | 17 ++++++++++++++++-
 1 file changed, 16 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker::test_write_then_clear_round_trips` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker::test_no_marker_is_a_silent_empty_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker::test_stale_marker_is_reported` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker::test_reconcile_reports_and_clears_a_stale_marker` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarkerSigterm::test_sigterm_between_marker_write_and_mutation_leaves_marker_for_reconcile` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 757 warning(s), 744 waived
- error-findings: none (measured, zero errors)
