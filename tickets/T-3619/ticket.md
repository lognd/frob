---
id: T-3619
title: 'windows CI diag round 9: ErrorActionPreference kills step on stderr, commitless
  fixture'
state: done
kind: bug
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/test_ci_workflow_matrix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_step_sets_error_action_preference_continue_first
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_fixture_repo_has_an_initial_commit
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33459475864: with T-3609's redirect removal, the diag step's real
death is finally visible. The child ran and printed:

  WARNING: gitio: git rev-parse --abbrev-ref HEAD failed (rc=128):
  fatal: ambiguous argument 'HEAD': unknown revision or path not in the
  working tree.
  frob: interrupted

then the STEP exited 1 at ~1.5s elapsed, with none of the script's own
Write-Host lines ever printing. Two defects:

1. GitHub Actions runs pwsh steps with $ErrorActionPreference='Stop'.
   Under Stop, a native command's FIRST stderr line becomes a
   terminating error -- the script died at the uv run line the moment
   frob printed that gitio WARNING to stderr. Round 8 removed the 2>
   redirect but kept Stop, so any stderr still kills the step. Fix: set
   $ErrorActionPreference = 'Continue' as the FIRST line of the step
   script. This is the mechanism that killed rounds 7 AND 8 too (round
   8: uv resolver chatter; round 9: frob's gitio warning).
2. The fixture repo is git init with ZERO COMMITS, so frob's gitio
   git rev-parse --abbrev-ref HEAD fails rc=128 and frob exits
   "frob: interrupted" (rc-coupled abort). Fix: after git init, create
   one empty commit:
   git -C $fixture -c user.email=ci@frob -c user.name=CI commit --allow-empty -m init
   (Also note for a possible separate frob bug: frob check on a
   commitless repo reporting "interrupted" instead of a clear
   NoCommitsYet message -- verify after the fixture fix whether this
   remains reachable; if so file a small frob ticket for it.)

Keep the elapsed-time discriminator and everything else from T-3604/
T-3609 unchanged. Scope: .github/workflows/ci.yml (+ its matrix test
file tests/test_ci_workflow_matrix.py if it asserts step content).