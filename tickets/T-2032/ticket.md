---
id: T-2032
title: frob coverage's xdist worker-crash retry appends -p no:xdist without removing
  -n, so the OOM recovery path always dies with a usage error and reports it as a
  REAL test failure
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/testing/_coverage_refresh.py
- tests/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/testing/_coverage_refresh.py
  reason: narrow to the retry-argv builder in _coverage_refresh.py and its test module;
    no other files needed for T-2032
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_coverage.py
  reason: narrow to the retry-argv builder in _coverage_refresh.py and its test module;
    no other files needed for T-2032
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_coverage.py::TestWorkerCrashRetryArgvStripsWorkerCount::test_retry_argv_contains_neither_n_flag_nor_its_value
- tests/test_coverage.py::TestWorkerCrashRetryUnmeasurableExitReporting::test_retry_exit_4_is_not_reported_as_a_real_failure
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery
designated_repro_test: tests/test_coverage.py::TestWorkerCrashRetryArgvStripsWorkerCount::test_retry_argv_contains_neither_n_flag_nor_its_value
threat: null
component: null
anchor: false
anchor_reason: null
---
## Problem

T-1672's OOM-recovery path in `frob coverage` can never succeed. When the
parallel pytest run matches the xdist worker-crash signature, the code
retries "serially" by APPENDING `-p no:xdist` to the original argv without
REMOVING the `-n <N>` flag that argv already carries:

    src/frob/testing/_coverage_refresh.py:722
        retry_argv = [*argv, "-p", "no:xdist"]

With the xdist plugin disabled, pytest no longer recognises `-n`, so the
retry dies with a usage error before running a single test. The recovery
path is structurally incapable of recovering.

## Measured evidence (2026-08-10, `uv run frob coverage --full` on main)

    coverage_refresh: spawning ['pytest', '--cov=src/frob', '--cov-report=', '-n', '12'] under watchdog
    ERROR: coverage_refresh: pytest --cov=src/frob --cov-report= -n 12 exited 3 and matched the
      xdist worker-crash signature (T-1672: a worker process was killed, most often OOM) --
      retrying ONCE serially (-p no:xdist) instead of discarding an already-mostly-passing run
    coverage_refresh: spawning ['pytest', '--cov=src/frob', '--cov-report=', '-n', '12', '-p', 'no:xdist'] under watchdog
    ERROR: coverage_refresh: serial retry after worker-crash still exited 4 -- this is a REAL
      failure, not the worker-crash artifact
    ERROR: coverage_refresh: coverage xml -i exited 1
    ERROR: frob coverage --full: `coverage xml` could not produce coverage.xml

Note the second spawn line: `-n 12` is still present alongside `-p no:xdist`.
Exit 4 is pytest's USAGE-ERROR code, not a test failure.

## The second, worse defect: the error message asserts the opposite

The retry's failure is reported as:

    "serial retry after worker-crash still exited 4 -- this is a REAL
     failure, not the worker-crash artifact"

That statement is false and actively misleading. It tells the operator their
test suite is genuinely broken, when in fact the retry command was malformed
and no test ever ran. An operator who trusts this line goes looking for a
non-existent test regression. This is the more expensive half of the bug:
a wrong diagnosis costs more than a failed command.

Exit 4 should never be interpreted as a test result at all. pytest exit codes
0/1/2/5 describe test outcomes; 3 is an internal error and 4 is a usage
error. Treating 4 as "a REAL failure" conflates "I could not run the tests"
with "the tests failed" -- the same confusion this repo has already ruled
against elsewhere (T-1664: semantic checks must report UNRESOLVED, never
silently pass or mis-report, when they cannot decide).

## Blast radius

The whole `frob coverage --full` path is unusable on any machine where the
parallel run OOMs. This directly blocked T-1953 (the TEST005 coverage-floor
ratchet), which requires a coordinator-run full-coverage measurement and
cannot proceed without a `coverage.xml`. OOM under `-n 12` is routine on this
host when several agents are running.

## Do NOT fix it this way

- Do NOT lower the default `-n` or otherwise "reduce the chance of OOM". That
  makes the crash rarer without making the recovery path work, so the same
  dead end returns under load -- and it slows every healthy run to paper over
  a broken branch.
- Do NOT drop the serial retry entirely and just fail fast. The retry exists
  for a real reason (T-1672: keeping an already-mostly-passing run rather
  than discarding it) and that reason still holds.
- Do NOT special-case exit 4 into the worker-crash signature so the message
  stops claiming "REAL failure". That silences the symptom while leaving the
  malformed command in place, and it would make a genuine usage error
  invisible.
- Do NOT fix only the argv and leave the exit-4 message. Both halves are
  real; the misleading diagnosis is the half that wastes an operator's time.

## Acceptance criteria

1. A test asserting the retry argv contains NEITHER `-n` NOR its value when
   `-p no:xdist` is added -- built from an argv that includes `-n 12`.
   THIS TEST MUST FAIL BEFORE THE FIX. Watch it fail and record the output.
2. A test that a pytest exit code of 4 (usage error) is reported as an
   inability to measure -- not as a test failure and not as a pass. The
   message must not assert "this is a REAL failure".
3. An end-to-end check that `frob coverage --full` produces a `coverage.xml`
   when the first parallel attempt is made to fail with the worker-crash
   signature.
4. Report whether any OTHER argv-mutating retry path in this module has the
   same append-without-removing shape. State the denominator you searched
   and the result, including if the answer is "none".