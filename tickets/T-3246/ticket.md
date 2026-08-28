---
id: T-3246
title: 'SUITE-RESULT reports an ABORTED run (exitstatus=3) in the same shape as a
  completed one: failed=24 is a lower bound read as a count'
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- tests/unit/test_conftest_suite_result_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_conftest_suite_result_status.py
  reason: T-3246's must-fire/must-stay-quiet fixtures for the DID-NOT-COMPLETE label
    live in a new file (test_conftest_stackdump.py was under a live T-3244 scope lease
    at land time)
  actor: logan
  at: '2026-08-28'
evidence:
- tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_labels_did_not_complete_runs
- tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_completed_run_format_is_unchanged
- tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_marks_failing_set_incomplete_on_abort
- tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_completed_run_never_marked_incomplete
- tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_names_internalerror_cause
- tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_configure_resets_stale_internal_error
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 02fffb975ff783bef880c0aef7c457948d0be99e
---
MEASURED from the CI run of 2026-08-28 (ubuntu and windows both).

    SUITE-RESULT: exitstatus=3 collected=12491 failed=24

exitstatus=3 is pytest's INTERNALERROR. The run ABORTED. It did not finish
collecting results, so `failed=24` is a LOWER BOUND of unknown looseness -- not
a failure count. The 24 `SUITE-RESULT-FAILED:` node ids that follow are whatever
had been recorded when the scheduler died, not the suite's failing set.

The emitter is `pytest_sessionfinish` in `tests/conftest.py:265`:

    line = f"SUITE-RESULT: exitstatus={exitstatus} collected={total} failed={failed}"

An aborted run (exitstatus=3) and a completed run with 24 real failures
(exitstatus=1) render in the SAME FORMAT, differing only in a single digit that
carries no label. Nothing in the line says "this run did not finish".

THIS IS THE PROJECT'S DOMINANT BUG CLASS, IN THE TEST HARNESS ITSELF. A failed
measurement is being reported in the shape of a successful one. It is worse here
than in most instances because this line is the repo's designated always-visible
summary -- it exists specifically so a reader does not have to re-run the suite
to learn what failed (T-1596/T-1673). It is the artifact everyone trusts.

I READ IT WRONG MYSELF, which is the proof it is misleading rather than merely
imprecise: presented with this output I began triaging the 24 node ids as a
failure list before noticing the exit status.

DO NOT FIX THIS BY SUPPRESSING THE LINE ON AN ABORTED RUN. The partial
information is valuable -- it is the only record of what ran before the abort.
The defect is that it is UNLABELLED, not that it exists.

WHAT TO BUILD:
  1. Classify the exit status explicitly in the line. pytest's documented codes:
     0 all passed, 1 tests failed, 2 interrupted, 3 internal error, 4 usage
     error, 5 no tests collected. At minimum distinguish COMPLETED (0/1) from
     DID-NOT-COMPLETE (2/3/4/5).
  2. On a did-not-complete run, the counts must be labelled as partial and the
     `SUITE-RESULT-FAILED:` block must say the failing set is INCOMPLETE.
  3. Where the abort cause is known (an INTERNALERROR traceback is in the
     output), name it.

MUST-FIRE FIXTURE: an aborted run (simulate exitstatus=3) produces a line that a
reader cannot mistake for a completed run, and an explicitly-incomplete failing
set.
MUST-STAY-QUIET FIXTURE: a normal completed run with real failures produces the
existing format, unchanged. The existing assertions in
`tests/unit/test_conftest_stackdump.py` (which assert the exact current string
for exitstatus=1) must still pass or be updated deliberately, not incidentally.

CHECK FOR SIBLINGS AND REPORT THEM, DO NOT FIX THEM HERE: anything else in this
repo that consumes a pytest exit code or a SUITE-RESULT line and branches only
on zero/non-zero is making the same conflation. `frob test`, the land pipeline's
gate spawn, and evidence recording are the places to look.