---
id: T-3249
title: 'Unowned 11-failure cluster: frob check fires spurious REF001/PRE001/SCOPE001
  only under concurrent load (T-2992 misattributed it to the already-landed T-3019)'
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
UNOWNED. T-2992's Done report attributes this cluster to T-3019 and states "NOT
double-filed, NOT double-fixed -- T-3019 owns this." BOTH HALVES OF THAT ARE
FALSE, measured 2026-08-28:

  - T-3019 was already DONE, landed at 0c4b152f5 on 2026-08-26 -- two days
    BEFORE the run that produced this histogram, and present in the tree that
    run measured (which was 2 commits behind main).
  - The cited repro, tests/system/test_cli_check.py::test_clean_code_exits_zero,
    PASSES in isolation on current main:
        SUITE-RESULT: exitstatus=0 collected=1 failed=0

So the cluster survived the fix it was attributed to, and has had no owner
since. Nothing is tracking it. I am filing it rather than leaving a closed
ticket's false reassurance standing.

THE CLUSTER (11 failures, from T-2992's Linux run of 12,035/12,039 tests, whose
Done report is on main at tickets/archive/T-2992/done-report.md):

    tests/system/test_cli_check.py            8
    tests/system/test_scaffold_dx.py          1
    tests/system/test_cli_native_missing.py   1
    tests/system/test_cli_perf.py             1

Reported symptom: `frob check` fires spurious REF001/PRE001/SCOPE001 on a
clean/scaffolded synthetic project.

THE CHARACTERISATION IN T-2992 IS WRONG AND MATTERS. It says these are spurious
findings "on any clean/scaffolded synthetic project". That predicts the repro
fails standalone. It does not -- it passes. The failures appear only in a
loaded, parallel, chunked run. So this is LOAD- OR CONCURRENCY-DEPENDENT, not a
property of clean projects. Anyone who takes the ticket on the original
description will try to reproduce it in isolation, succeed at passing, and
conclude it is fixed.

INDEPENDENTLY REPRODUCED ON CI. The 2026-08-28 CI run (ubuntu) failed exactly
this file set: test_cli_check.py (3), test_cli_native_missing.py (2),
test_cli_perf.py (3), test_scaffold_dx.py (1). Treat that run's list as
CORROBORATION OF THE FILE SET ONLY, not as counts -- it aborted with
exitstatus=3 (INTERNALERROR, see T-3246) so its numbers are a lower bound.

PRIOR ART, SAME SIGNATURE, ALREADY FIXED ONCE: T-0089 (done) is titled
"test_scaffold_dx flaky under full-suite run, passes in isolation" and its
recorded evidence is
tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
-- the very test failing again here. T-0089 was blocked_by T-0122 ("frob check
races concurrent build_graph calls against shared .frob/cache.db", also done).
Read both before starting. Either their fix regressed, or it was narrower than
the class. Determining WHICH is the first job; do not assume regression.

LIKELY DIRECTION, NOT VERIFIED -- MEASURE IT: shared mutable state across
concurrently-running system tests. `.frob/cache.db`, the graph cache, a memo
layer, or cwd contention are the candidates T-0122 already implicated. Several
tickets this drive asserted a cause that was never verified; do not add another.

DO NOT FIX THIS BY MARKING THE TESTS FLAKY, RETRYING THEM, OR SERIALISING THEM
AWAY. If `frob check` reports findings that depend on whether another check is
running concurrently, that is a product defect and users hit it -- the tests are
the messenger. A retry decorator would hide the only detector we have.

ACCEPTANCE
- A reproduction under load, with the exact command and the conditions needed.
  "Passes in isolation" is a required part of the repro, not a caveat.
- Root cause identified with evidence, and a stated answer to whether T-0089/
  T-0122's fix regressed or was too narrow.
- A fix in the product where the defect is in the product.
- A regression test that fails under the concurrent conditions before the fix.
- T-2992's false attribution corrected -- but its Done report is on main as a
  historical artifact and must NOT be rewritten. Record the correction here.
