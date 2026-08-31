---
id: T-3560
title: 'Windows KeyboardInterrupt round 3: serial mode falsified execnet; land -v
  --full-trace + SIGBREAK faulthandler instrumentation, then fix the named culprit'
state: in-progress
kind: bug
origin: agent
created: '2026-08-31'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/conftest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: BUG002 needs an explicit waiver for a CI-only diagnostics land with no reproducible
    in-repo test
  actor: logan
  at: '2026-08-31'
  old_length: 2467
  new_length: 2888
evidence:
- tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group
- tests/unit/test_release_workflow_gate.py::TestReleaseWorkflowNoAutomaticTrigger::test_only_workflow_dispatch_trigger
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Round 3 of the Windows early-KeyboardInterrupt (T-3540 console fix and
T-3549 serial mode both landed and both FALSIFIED as the cause).
MEASURED on run 33367854833 (HEAD e1974b649, windows-latest, -p no:xdist
in effect -- proven by the PytestUnknownMarkWarning for xdist_group):
plain SERIAL pytest still dies with `!!! KeyboardInterrupt !!!` at
threading.py:1169 (Thread.join) after ~4 minutes, at roughly collection
position 130 of 13000 [1%]; pytest catches it cleanly (warnings summary
prints), exit 1. Same fractional death point across three xdist runs and
this serial run. `git grep` finds ZERO senders of
CTRL_C_EVENT/interrupt_main/os.kill(SIGINT) in tests/, src/, .claude/ --
nothing in-repo raises it directly. Serial collection order puts position
~120-137 inside tests/integration/test_gitlog.py (18 tests, spawns git
subprocesses), with tests/integration/test_integration.py and
tests/system/test_ci_hang_guard_positive_control.py (win32-skipped pair,
the "ss" in the progress dots) shortly after.

TWO HYPOTHESES LEFT:
 a. Position-bound: an early test (gitlog/integration neighborhood) spawns
    a subprocess sharing the console whose termination path delivers a
    console ctrl event to the whole group (e.g. taskkill, or a child that
    installs a console handler); the join frame is pytest waiting on a
    watcher thread while the ctrl event hits the main thread.
 b. Time-bound: an external actor fires at ~4 min into the Test step on
    the runner (cache post-step, antivirus, a leaked timer from an
    earlier step) -- weaker, but not excluded.

DELIVERABLE (two lands):
 1. INSTRUMENTATION land: windows-latest Test step only, add `-v
    --full-trace` (so the dying test is NAMED and the interrupt traceback
    is complete) and register faulthandler on SIGBREAK in a win32-only
    conftest guard; keep it clearly commented as temporary T-<this>
    diagnostics. Coordinate with the ci.yml comment blocks.
 2. After the next windows run: read the named culprit + full trace from
    the log, fix the root cause (likely CREATE_NEW_PROCESS_GROUP /
    CREATE_NEW_CONSOLE on the culprit's subprocess spawn, or a win32
    PLATFORM001 boundary), and REVERT the instrumentation in the same
    land. If the trace instead proves hypothesis (b), document it and
    propose the mitigation.
ACCEPTANCE: a windows-latest run proceeds past 5% (any failure shape is
fine -- the interrupt specifically is gone), and the instrumentation is
reverted.

frob:waive BUG002 reason="this is a temporary CI diagnostics-only land (adds -v --full-trace and a win32-only SIGBREAK faulthandler registration to observe an intermittent windows-latest-only interrupt); the defect itself is an external Windows CI runner condition that cannot be reproduced by this suite -- no in-repo test can fail-at-main/pass-at-fix for it, same posture as frob ticket land --skip-mutation-evidence"