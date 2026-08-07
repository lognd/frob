## Done report

TICK009 no longer fires on QUEUED tickets; surfaced at start time instead (T-1645).

Confirmed the bug directly: `_tick009_scope_breadth_nudges` (src/frob/gates/_tickets_gate.py)
evaluated every ticket in `IN_PROGRESS`/`QUEUED`/`PLANNED` state -- QUEUED
included, demanding file-level precision for a scope declared before
anyone had opened the code. Measured on this repo's own ledger before
the fix: 48 tickets carried TICK009, ~204 findings total.

Fix (same lifecycle principle as T-1639, applied here per the ticket's
own explicit ask to implement them consistently):
- `_tick009_scope_breadth_nudges` now evaluates only `PLANNED`/
  `IN_PROGRESS` tickets -- QUEUED produces zero TICK009 findings,
  regardless of scope breadth. DONE/DROPPED/BLOCKED unaffected (already
  excluded before this change, for DONE/DROPPED; BLOCKED was never
  evaluated either way since it wasn't in the original tuple).
- `frob.app.ticket_runner._query._active_large_glob_warnings` (backs
  `frob ticket doable`'s scope-breadth summary count) updated the same
  way -- its own docstring claims it mirrors TICK009's detail, so leaving
  it including QUEUED would have silently made `doable`'s summary count
  disagree with what `frob check` actually reports.
- New: `frob.app.ticket_runner._lifecycle._warn_scope_breadth_on_start`,
  called at the end of `frob ticket start` (right after the queued/
  planned -> in-progress transition commits) -- surfaces the exact same
  `large_glob_warnings` nudge directly to the author in the moment they
  have the code open, per the ticket's own "far more actionable" framing.
  Pure disclosure (a WARNING log line), never blocks or exits nonzero.

Measured after the fix (`frob check --only tickets --json`, this
worktree's own branch): 2 TICK009 findings, both for T-1634 (this
worktree's own in-progress ticket, correctly still firing since it is
genuinely IN_PROGRESS with a broad-by-necessity scope) -- down from the
repo's pre-fix 48-ticket / ~204-finding baseline, matching the ticket's
"roughly 100 warnings" expectation (T-1634's own scope entries account
for the 2 remaining, all others were QUEUED and are now silent).

Changed:
- src/frob/gates/_tickets_gate.py::_tick009_scope_breadth_nudges
- src/frob/app/ticket_runner/_query.py::_active_large_glob_warnings
- src/frob/app/ticket_runner/_lifecycle.py::_warn_scope_breadth_on_start (new)
- docs/modules/gates.md -- TICK009 table entry + "TICK009/TICK010" section updated
- tests/test_gates_tick009_tick010.py -- existing QUEUED-state assertions
  moved to PLANNED (the state still evaluated); two new tests added
  (QUEUED-silent, IN_PROGRESS-still-fires)
- tests/unit/test_app_runners_t0714_doable_summary.py -- same QUEUED ->
  PLANNED update plus a new QUEUED-silent test
- tests/unit/test_app_runners_batch7.py -- two new tests for the new
  start-time nudge

Tests added:
- tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_queued_ticket_no_finding_even_with_broad_scope
- tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_in_progress_over_broad_glob_still_warns
- tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary::test_queued_tickets_never_contribute_a_nudge
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_warns_on_over_broad_scope
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_precise_scope_warns_nothing

Verification:
- `uv run pytest tests/test_gates_tick009_tick010.py tests/unit/test_app_runners_t0714_doable_summary.py tests/unit/test_app_runners_batch7.py -k "TestTick009ScopeBreadthNudges or TestRenderScopeBreadthSummary or TestTicketStart"` -- 17 passed
- `uv run frob check --ticket T-1645` -- 0 errors other than the one
  land-absorbed SELFAUDIT001 (testsuite interface-sync entry `frob
  ticket land` writes automatically before its own merge)
- `uv run frob check --land-parity` -- clean, 0 unscoped errors (confirms
  the SELFAUDIT001 above resolves at land, not a real gap)

Not done: the ticket explicitly says "do NOT resolve this by raising the
25-file threshold" -- confirmed `_over_broad_scope_entries`'s threshold
logic is completely untouched; only the STATE gate changed.

T-1639/T-1645/T-1614 (named together in this ticket's body) are the same
underlying issue: frob treating a declaration made before work
identically to one made during it. T-1639's report covers the
CrossTicketLeakage instance; I did not find a third instance within this
ticket's own scope (src/frob/gates/_tickets_gate.py plus the two files I
scope-added for consistency). T-1614 (the waiver audit) is out of scope
here and not investigated.

### Changed
```
 docs/guides/install.md                       |  42 +++-
 docs/modules/app.md                          |   6 +-
 docs/modules/render.md                       |   5 +-
 docs/modules/tickets.md                      |  35 +++
 src/frob/app/doctor_runner.py                |  26 +++
 src/frob/doctor.py                           |  93 +++++---
 src/frob/tickets/_land.py                    | 132 ++++++++++-
 tests/system/test_cli_doctor.py              |  60 ++++-
 tests/test_ticket_land.py                    |  97 ++++++++
 tests/unit/test_doctor_runner_t1276.py       |  71 +++++-
 tests/unit/test_land_cross_ticket_leakage.py |  69 ++++++
 tickets-archive.md                           |   3 +-
 tickets.md                                   | 321 ++++++++++++++++++++++++++-
 13 files changed, 896 insertions(+), 64 deletions(-)
```

### Evidence
- `tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_queued_ticket_no_finding_even_with_broad_scope` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_chronically_over_broad_glob_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_in_progress_over_broad_glob_still_warns` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary::test_queued_tickets_never_contribute_a_nudge` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary::test_multiple_stale_leases_collapse_to_one_summary_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_warns_on_over_broad_scope` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_precise_scope_warns_nothing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 1059 warning(s), 851 waived
- error-findings: none (measured, zero errors)
