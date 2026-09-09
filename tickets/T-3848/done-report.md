## Done report

Both-errors decision: the returned error stays the ORIGINAL merge/finalize
error (LandError like NotFound) -- still what determines why THIS land
failed and what every existing caller/test branches on. The unwind failure
(if any) surfaces via a CRITICAL log line naming BOTH errors by their
LandError value plus an explicit "root may be inconsistent, half-unwound"
warning. A dedicated new LandError member (e.g. UnwindAlsoFailed) would be
the more complete signal for an automated caller, but src/frob/tickets/
_models.py (where LandError lives) was leased by another in-progress ticket
(T-3852) at fix time and is outside this ticket's declared scope -- left for
whichever ticket next touches LandError with _models.py free.

Enumeration of _land_plan_locked's cleanup/compensating calls on a failure
path:
- merge/finalize failure branch (line ~2404 pre-fix): discarded the unwind
  Result outright -- THE bug, fixed here via
  _land_plan_unwind_after_merge_failure.
- _land_plan_tick_gate_dirty's own unwind call: already correctly assigned
  to `unwound` and inspected via `.is_err` before this fix.
- _land_plan_finish's dry-run reset tail: already correctly assigned to
  `unwound` and inspected via `.is_err` before this fix.
So this was the ONE true discard among three unwind call sites in this
function.

Changed:
- src/frob/tickets/_land.py::_land_plan_unwind_after_merge_failure (new)
- src/frob/tickets/_land.py::_land_plan_locked (call site fixed)

Evidence:
- tests/ticket_land_suite/test_land_plan.py::TestLandPlanUnwindAfterMergeFailureSurfaces::test_double_failure_logs_both_and_still_reports_the_merge_error (MUST-FIRE, real injected double failure)
- tests/ticket_land_suite/test_land_plan.py::TestLandPlanUnwindAfterMergeFailureSurfaces::test_successful_unwind_reports_only_the_merge_error (MUST-STAY-QUIET)

Filed: none

Gates: frob check --ticket T-3848 clean except gate:COV:COV003 on T-4346's
evidence (a different, unrelated ticket's business) and the transient
gate:PRE PRE001 stale-sweep flag (re-swept before evidence/close).
