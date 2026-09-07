---
id: T-4257
title: 'fix the Windows infrastructure test failures: stale gate-cache hit, land attribution,
  out-of-tree release bump, and the strata GIL timeout'
state: in-progress
kind: bug
origin: human
created: '2026-09-07'
priority: high
parent: T-4236
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_gate_cache.py
- tests/test_ticket_land_lint_diff_attribution.py
- tests/unit/test_land_release_out_of_tree.py
- tests/unit/strata/test_strata_core_gil.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a changed gate input on Windows, when the gate cache is consulted, then
    it misses rather than returning a stale verdict, and the invalidation key is shown
    to have adequate resolution there
  evidence: []
- text: given the Windows runner, when the land attribution and out-of-tree release-bump
    tests run, then both pass and the report says whether they shared one cause
  evidence: []
- text: given the strata core global-interpreter-lock test on Windows, when it is
    diagnosed, then a captured stack shows whether the product deadlocks or the runner
    is merely slow, and the fix matches that finding rather than raising a limit
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE WINDOWS INFRASTRUCTURE FAILURE GROUP. Four tests fail on the Windows CI leg
for reasons rooted in platform infrastructure rather than in path shape or in
child-process encoding. They are disjoint from the other two open leaves under
this epic and can be worked in parallel with both.

WINDOWS IS VERIFIABLE LOCALLY. Do not reason about Windows behaviour from a
Linux shell, and never write that a fix is unproven until CI. The global winrun
script syncs this repository to a Windows mirror and runs a command there
natively through PowerShell. Measure the actual failing assertion on real
Windows BEFORE you change anything, and measure it again AFTER. A fix that was
never observed to change a Windows-side value is not evidence. The Windows
virtualenv puts its executables in a Scripts directory, not a bin one.

THE FOUR FAILURES, AND WHAT MAKES EACH ONE INTERESTING.

First, the gate cache test observes a stale cache HIT where it expects a miss.
This is the highest-value item in the group and it is very likely a real product
defect rather than a test artifact. A cache that fails to notice a changed input
returns a stale verdict, and a stale verdict from a gate is a silent pass. Find
what the invalidation key is built from and whether that input has the same
resolution on Windows as it does here. File-modification timestamp granularity
is a common culprit and it is worth measuring directly rather than assuming.
Note independently that this repository's own cache database has been observed
corrupt more than once under concurrent writers, so if you find a locking or
durability weakness while you are in this code, record it rather than losing it.

Second and third, the land lint-diff-attribution test and the out-of-tree
release-bump test both exercise land infrastructure on a platform where the
temporary directory, the drive letter, and the file-locking semantics all differ
from what the code was written against. Determine for each whether the failure
is the same underlying cause; if it is, fix it once.

Fourth, the strata core global-interpreter-lock test times out. A timeout is not
a failure message and tells you almost nothing on its own, so the first task is
to obtain the actual stack of the stuck process rather than guessing at it. A
faulthandler dump under a timeout that sends an abort signal will print where it
is stuck in one command. Decide from that stack whether the product deadlocks on
Windows or whether the test's timing assumption is simply too tight for a slower
runner. Those two conclusions call for opposite fixes, so do not choose between
them without the stack.

DO NOT WIDEN A TIMEOUT TO MAKE A TEST PASS unless you have the stack showing the
work genuinely completes and only needs longer. Raising a limit to silence a
deadlock hides the defect and is the wrong incentive.
