---
id: T-4274
title: the macos test step exceeds its budget and is killed with no result, and the
  abort-signal stack dump built to diagnose exactly this produced no stack
state: in-progress
kind: bug
origin: human
created: '2026-09-07'
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
- tests/test_ci_workflow_timeout.py
- tests/test_ci_workflow_matrix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ci_workflow_timeout.py
  reason: added the T-4274 regression-lock tests to this file and fixed a stale literal-match
    assertion in the sibling matrix test that the invocation-shape change broke
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_ci_workflow_matrix.py
  reason: added the T-4274 regression-lock tests to this file and fixed a stale literal-match
    assertion in the sibling matrix test that the invocation-shape change broke
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
acceptance:
- text: given a process deliberately hung under the macos step's own harness, when
    the budget expires and the abort signal is sent, then a stack dump appears in
    the step output or the teed log
  evidence: []
- text: given that working stack dump, when the macos leg next exceeds its budget,
    then the decision between a slow suite, a genuine hang, and an undersized budget
    is made from the stack rather than assumed
  evidence: []
- text: given the macos leg, when it completes, then the margin between its duration
    and its budget is reported so a near-miss is visible before it becomes a failure
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE MACOS TEST STEP NOW EXCEEDS ITS FORTY-MINUTE BUDGET AND IS KILLED WITH NO
RESULT, AND THE MECHANISM BUILT TO DIAGNOSE EXACTLY THIS PRODUCED NO STACK.

WHAT THE RUN SHOWED. The macos leg emitted no suite-result line at all. Its test
step ran to the 2,400-second budget, the workflow announced that it was sending an
abort signal for a stack dump before the kill, and the process died with an abort
trap and exit code 134. The job then terminated ten orphaned processes during
cleanup, most of them interpreters.

THE MARGIN WAS ALREADY GONE AND NOBODY HAD NOTICED. On the previous complete run,
the same leg finished in about thirty-nine minutes against a forty-minute budget.
That is not a comfortable pass; it is a pass by roughly one minute. A suite that
grew slightly, or a slower runner allocation, is enough to convert it into this,
and that appears to be what happened. Treat the earlier green as the warning it
was rather than as evidence the budget was adequate.

DO NOT ASSUME A DEADLOCK, AND DO NOT ASSUME MERE SLOWNESS. The evidence supports
"did not finish in the allotted time" and nothing more specific. The orphaned
interpreters at cleanup are suggestive of work still in flight but are equally
consistent with a suite killed mid-run. The linux leg, running the same suite,
completed and reported a full count. Resolving which of these it is requires the
diagnostic below, which is why that half comes first.

THE DIAGNOSTIC FAILED, AND THAT IS THE MORE IMPORTANT DEFECT. The whole purpose
of signalling an abort rather than killing outright is to obtain a stack showing
where the process was stuck. No stack appeared -- not in the step output, and not
in the log file the step tees into and later greps. So the mechanism spent the
budget, killed the run, and produced exactly the information it exists to
produce, which is none. Work out why: the plausible candidates are that the
faulthandler environment variable is not set for this process, that the dump went
to a stream the process substitution discards, or that the abort killed the
process before the dump could flush. All three are testable locally.

THIS IS THE THIRD DIAGNOSTIC IN ONE DAY THAT REPORTED NOTHING WHEN ASKED. A land
status marker named a finished land while a different one ran; a daemon status
verb returned a payload too large to read while announcing its own baseline was
stale; and now a hang dump produced no stack. Each was built to answer a question
and each failed at the moment it was asked. The pattern is worth naming in the
fix: a diagnostic that is not itself exercised is not a diagnostic, it is an
intention.

A CONSEQUENCE FOR THE RELEASE, RECORDED SO IT IS NOT LOST. Because both posix
legs failed inside their test steps, the gate step was skipped on both, and the
gate step is also skipped on the windows leg for the same reason. So no platform
has run the gates against the current tree, and the gate fixes landed earlier
today remain unverified by the integration run rather than confirmed by it.

ORDER OF WORK. Fix the dump first and prove it produces a stack under a forced
hang. Only then re-run and read what the stack says before deciding whether the
answer is a slow suite, a genuine hang, or a budget that was never sized for this
platform. Raising the budget without that stack would be a guess, and would also
be the second time today a limit was raised in place of an explanation.