---
id: T-3250
title: 'macOS CI hangs at 99% for 10m49s with ZERO diagnostics: T-3192 instrumented
  only ubuntu on a premise this run falsifies'
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
- .github/workflows/ci.yml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-3250: BUG002 cannot be satisfied without a scope violation (ticket scope
    is ci.yml only, no test files); the defect is a live-CI-only silent hang not locally
    reproducible, and behavioral test coverage for the new guard mechanisms is deferred
    to T-3274'
  actor: logan
  at: '2026-08-28'
  old_length: 4807
  new_length: 5605
evidence:
- tests/test_ci_workflow_timeout.py::TestBuildJobHasATimeoutBackstop::test_build_job_declares_timeout_minutes
- tests/test_ci_workflow_timeout.py::TestUbuntuTestStepIsTimedWithStackDump::test_ubuntu_test_step_wraps_pytest_in_timeout_abrt
- tests/test_ci_workflow_timeout.py::TestUbuntuTestStepIsTimedWithStackDump::test_ubuntu_test_step_enables_faulthandler
- tests/test_ci_workflow_timeout.py::TestUbuntuTestStepIsTimedWithStackDump::test_ubuntu_test_step_only_applies_on_linux
- tests/test_ci_workflow_timeout.py::TestUbuntuTestStepIsTimedWithStackDump::test_a_non_gated_pytest_step_still_exists_for_other_platforms
- tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_job_declares_a_matrix_strategy
- tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_includes_windows_and_macos
- tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_is_fail_fast_false
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED from CI run 33169097371, job build (macos-latest) 98841565692,
2026-08-28. This falsifies a premise T-3192 wrote down and relied on.

WHAT HAPPENED. The macOS Test step reached 99% and then went SILENT FOR 10
MINUTES 49 SECONDS before the job-level backstop killed it:

    12:31:23.5805490Z  ...............................................  [ 99%]
    12:42:12.9722850Z  ##[error]The operation was canceled.

Job wall time 45m25s -- i.e. it ran to `timeout-minutes: 45` exactly. This is
NOT aggregate slowness: 99% of ~12,500 tests completed, the last progress line
landed at 12:31, and then nothing. macOS HUNG.

It produced ZERO diagnostic output. No stack dump, no failing node ids, no
SUITE-RESULT line. A red X and nothing else -- precisely the pre-T-3192 failure
mode that T-3192 exists to end.

THE FALSIFIED PREMISE. `.github/workflows/ci.yml` splits the Test step per-OS
and instruments ONLY ubuntu:

    - name: Test (ubuntu, timed with stack-dump-on-hang)
      if: runner.os == 'Linux'
      env: {PYTHONFAULTHANDLER: "1"}
      run: timeout -s ABRT 25m uv run pytest -q
    - name: Test (windows/macos)
      if: runner.os != 'Linux'
      run: uv run pytest -q

The comment above it states the justification explicitly: "windows/macos have
never hung in this matrix's own history" and "ubuntu is also the ONLY platform
that has ever hung here, so this step is split per-OS rather than reaching for a
cross-platform equivalent that has no real hang history to justify it."

That reasoning was sound when written and is now REFUTED BY EVIDENCE. macOS has
hung. The same comment also budgets against "macOS's own Test stage completed in
~23 minutes when it last ran cleanly" -- this run went past 45.

Note what worked, so the fix is not overcorrected: on the SAME run, ubuntu's
instrumented step DID fire at 25m and produced full faulthandler stack dumps
naming the wedged frames. The instrumentation is correct. Its SCOPE is wrong.

THE SECOND, INDEPENDENT FINDING -- DO NOT MISS THIS. `pyproject.toml` sets
`faulthandler_timeout = 100` and `--timeout=120 --timeout-method=thread`, and
those are PLATFORM-INDEPENDENT: they fired on Windows in this very run (the
Windows job's dumps are stamped "Timeout (0:01:40)"). On macOS, during a 10m49s
silence, NEITHER fired. A per-test 120s cap cannot explain a 649-second gap.

HYPOTHESIS, NOT VERIFIED -- MEASURE IT: the hang is not inside a test, so no
per-test timeout applies. At 99% the remaining work is the final tests plus
session teardown and xdist worker shutdown. A lingering non-daemon thread, an
un-reaped subprocess, or a worker that never terminates would produce exactly
this signature. `--timeout-method=thread` also cannot interrupt a blocked C call
or a subprocess wait, which is a second candidate. Determine which; do not
assert a cause that was never verified.

WHAT TO BUILD:
  1. Instrument macOS and Windows to the same standard as ubuntu. GNU `timeout`
     is genuinely absent on BSD/pwsh userland -- that part of the original
     reasoning still holds -- so find the portable equivalent rather than
     copying the command. `PYTHONFAULTHANDLER=1` is portable and already proven
     on Windows here; a Python-level or step-level budget is the missing half.
     State what you chose and why it works on both.
  2. Cover the teardown/shutdown window that per-test timeouts structurally
     cannot reach. That is where this hang lives.
  3. The premise in the ci.yml comment must be corrected in the same change.
     Leaving "windows/macos have never hung in this matrix's own history" in the
     file after this run would be a false statement in the repo's own reasoning.

DO NOT FIX THIS BY RAISING `timeout-minutes: 45`. The backstop did its job. The
defect is that it is the ONLY thing standing between a macOS hang and an
infinite job, and it reports nothing.

MUST-FIRE FIXTURE: a planted hang on a non-Linux runner produces a stack dump
and a timed failure, not a bare cancellation. There is already a positive
control for the Linux side (tests/system/test_ci_hang_guard_positive_control.py)
that plants a real 600s hang -- extend that pattern rather than inventing a new
one. NOTE: that control itself failed on this run and is under investigation in
T-3247; check its status before building on it.
MUST-STAY-QUIET FIXTURE: an ordinary passing suite on macOS/Windows is
unaffected and does not pay a timeout penalty.

ACCEPTANCE
- macOS and Windows Test steps produce diagnostic output on a hang.
- The teardown-window gap is covered, or its exclusion is DECLARED with a stated
  reason (PLATFORM001 doctrine: declare the boundary, never degrade silently).
- The falsified premise corrected in ci.yml.
- A stated answer to why faulthandler_timeout/--timeout did not fire during the
  649-second silence.

frob:waive BUG002 reason="CI-only hang defect: the macOS/Windows silent-hang behavior this fixes can only be observed on a real GitHub Actions runner over a 10+ minute wall-clock window, not reproduced deterministically by this repos local pytest suite. The ticket scope is restricted to .github/workflows/ci.yml only (no test files), so no diff-touched-code repro test can be bound here; behavioral coverage of the new macOS kill -ABRT and Windows Wait-Process/Stop-Process mechanisms is tracked separately as T-3274 (extend tests/system/test_ci_hang_guard_positive_control.py). Bound evidence (tests/test_ci_workflow_timeout.py, tests/test_ci_workflow_matrix.py) is structural/confirmatory by necessity, verifying the workflow still declares the required steps/matrix shape." follow_up="T-3274"