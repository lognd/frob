---
id: T-4269
title: the windows test step takes 57 minutes against its own budget, and because
  it fails the gate step is skipped so gates have never run on windows
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
- .github/workflows/ci.yml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ci_workflow_matrix.py::TestSelfGateRunsOnWindowsEvenIfTestStepFails::test_self_gate_step_runs_on_windows_after_a_prior_failure
designated_repro_test: null
acceptance:
- text: given a passing windows test step, when the job continues, then the gate step
    actually runs on windows and its result is recorded for the first time
  evidence:
  - tests/test_ci_workflow_matrix.py::TestSelfGateRunsOnWindowsEvenIfTestStepFails::test_self_gate_step_runs_on_windows_after_a_prior_failure
acceptance_amendments:
- op: remove
  index: 2
  old_text: given that measurement, when a fix is chosen, then it addresses the measured
    cause and does not consist of raising the budget unless the measurement shows
    the work is genuinely that large
  new_text: null
  reason: T-4269 scoped down to acceptance [3] only per direct dispatch instruction;
    per-test time decomposition and its fix (was [1]/[2]) carried forward to T-draft-226a2b6c
  actor: logan
  at: '2026-09-09'
- op: remove
  index: 1
  old_text: given a completed windows leg, when its test step duration is measured,
    then where the time goes is established per test or per file rather than estimated
  new_text: null
  reason: T-4269 scoped down to the gate-decoupling change only, per direct dispatch
    instruction; per-test time decomposition carried forward to T-draft-226a2b6c
  actor: logan
  at: '2026-09-09'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE WINDOWS TEST STEP TAKES FIFTY-SEVEN MINUTES, WHICH IS MOST OF ITS OWN BUDGET,
AND THAT MARGIN IS THE REAL RISK RATHER THAN THE DURATION ITSELF.

MEASURED, from a step-level decomposition of a completed integration run rather
than from an estimate. The Windows job ran sixty-four minutes end to end. One
step accounted for 3,424 seconds of that: the Windows test step. Everything else
in the job together came to a few minutes, including the diagnostic scaffolding
that was removed separately and turned out to cost 174 seconds in total. For
comparison, the same run's linux leg finished in about thirty minutes and the
macos leg in about thirty-nine, each of those covering the tests AND the gate
step that Windows never reaches.

WHY THE MARGIN MATTERS MORE THAN THE NUMBER. The workflow carries a python-side
total budget and an outer process-wait backstop for this step, and the measured
run came in under the inner budget but not by a comfortable amount. A suite that
grows, a slower runner allocation, or a single hanging test moves this from a
failing step with readable output to a budget-expiry with a truncated log, which
is a much worse thing to debug. The project has already spent one long
investigation on a Windows hang; this is the conditions for a second one.

A CONSEQUENCE THAT IS EASY TO MISS. Because the test step fails, every step after
it is skipped, and that includes the gate step. So the gates have NEVER run on
Windows in this workflow. Any statement that the gates are platform-agnostic, or
that a given gate finding does or does not appear on Windows, is currently
unmeasured rather than known. Making the test step pass is what turns that
unknown into an observation.

WHAT TO ACTUALLY DO HERE, IN ORDER. First establish where the time goes: which
tests or which phase dominate, measured per-test or per-file rather than guessed.
Only then decide whether the answer is parallelism that is not being applied on
this platform, a small number of pathologically slow tests, per-test overhead
that is structurally higher here, or genuine extra work. Those have different
fixes and only one of them is a configuration change.

DO NOT RAISE THE BUDGET AS THE FIX. A larger budget converts a fast red into a
slow red and buys nothing. If the measurement shows the work is genuinely that
large and correct, then a budget change is a defensible conclusion, but it is a
conclusion, not an opening move.

NOTE THAT THIS IS NOT A CORRECTNESS TICKET. The Windows failures themselves are
tracked under the platform epic and its leaves. This ticket is only about how
long the step takes and how little headroom is left.

## Failure log
- 2026-09-08 attempt 1: Owning agent died before any work: the worktree holds only the start-transition commit, no source edits, no activity in over three hours. Requeued rather than left in-progress because the stale lease on .github/workflows/ci.yml refused a legitimate scope change on T-4305 (see T-4311). Windows is advisory-only (continue-on-error, T-3425) so this is not release-blocking; re-dispatch after the alpha. No work is lost.