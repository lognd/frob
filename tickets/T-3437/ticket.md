---
id: T-3437
title: 'T-3420 follow-up: test_coverage.py still asserts sigterm is True, and the
  SIGTERM must-fire fixture fails on macOS'
state: in-progress
kind: bug
origin: agent
created: '2026-08-29'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_coverage.py
- tests/system/test_coverage_sigterm.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given HEAD on macos-latest and ubuntu-latest, when tests/test_coverage.py
    and tests/system/test_coverage_sigterm.py run, then both pass
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3420 (344eba4db) set `sigterm = false` under [tool.coverage.run] to stop the
coverage.py SIGTERM-handler re-entrancy deadlock. MEASURED on GitHub Actions run
33281416850 (macos-latest, HEAD b872da691) that this landed two regressions
the touched-set run did not catch:

1. tests/test_coverage.py::TestPyprojectDeclaresCoverageConcurrency::
   test_pyproject_declares_concurrency_and_sigterm  (T-1235)
       assert coverage_run["sigterm"] is True
   This test encodes the OLD decision. T-3420's Done report is the newer,
   measured decision (upstream coveragepy#1101/#1340 open, 7.14.1 installed).
   Flip the assertion to `is False` and rewrite its docstring to cite T-3420
   and the deadlock mechanism, so the next reader sees WHY the value is false.
   Also check tests/test_coverage.py:879-890 (`test_rc_declares_multiprocessing_and_sigterm`,
   asserts "sigterm = True" in a generated rc text) -- decide whether that
   generator must also emit false (it should: one home for the setting) and
   fix the generator + test together, never just the test.

2. tests/system/test_coverage_sigterm.py::TestCoverageSigtermDeadlock::
   test_repeated_sigterm_terminates_in_bounded_time  (the T-3420 must-fire
   fixture) fails on macOS at
       _send_signal_to_group(proc.pid, signal.SIGTERM)  # lands inside the window
   The log shows no exception text beyond the frame; reproduce the failure
   mode by reading the helper: the likely causes are (a) the child already
   exited before the second signal (ProcessLookupError / ESRCH), or (b) the
   child was not started in its own process group on macOS so killpg
   targets the wrong group. Make the fixture robust on POSIX generally
   (tolerate ESRCH once the child has exited -- that IS the must-fire
   outcome), never skip it on macOS.

Verification: run BOTH files by node id with `-p no:xdist`; the ubuntu job
passed the first test only because ubuntu was killed at 99% before it.

MUST-FIRE:        reverting sigterm to true fails test_pyproject_declares_concurrency_and_sigterm.
MUST-STAY-QUIET:  both files pass on Linux locally with no skip markers added.
