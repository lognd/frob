---
id: T-4142
title: nine named failures plus two suspected-OOM worker deaths survive the CI regression
  fixes, from a run that did not complete and is a lower bound
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the full test suite, when it is run on a machine with enough headroom
    to finish, then it completes without a scheduler abort and reports its failing
    set as complete
  evidence: []
- text: given each surviving failure, when it is triaged, then it is classified as
    a regression, pre-existing debt, or unmeasured, with evidence for the classification
  evidence: []
- text: given every self-scan test that is retained, when a real finding of its kind
    is introduced, then that test fails
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
NINE NAMED TEST FAILURES PLUS TWO SUSPECTED-OOM WORKER DEATHS SURVIVE THE CI
REGRESSION FIXES, and the run that found them DID NOT COMPLETE, so this list is a
LOWER BOUND and not the failing set.

MEASURED 2026-09-07 by a broad run after T-4130 and T-4136 landed:

    tests/unit/                6419 tests, 0 failures   -- fully clean
    tests/ (everything else)   9 named failures + 2 worker deaths, INCOMPLETE

THE INCOMPLETENESS IS THE MOST IMPORTANT LINE IN THIS TICKET. The run aborted on
an xdist scheduler error after roughly 99% collection, consistent with the
machine's memory pressure at the time, and its own output said so explicitly:
DID-NOT-COMPLETE, failed=11 partial, lower-bound, failing set INCOMPLETE. Large
parts of gates_suite, integration, ticket_land_suite, vet_suite and the rest of
system never ran. TREAT THE UNEXECUTED REMAINDER AS UNMEASURED, NOT CLEAN. This
repo's own conftest was given that DID-NOT-COMPLETE labelling precisely because a
partial list was once read as a complete one.

THE NINE NAMED FAILURES:

    tests/system/test_artifact_smoke.py
      ::TestArtifactSmokeMustStayQuiet::test_current_pin_passes_serve_extra_check
      ::TestArtifactSmokeMustFire::test_unbounded_mcp_pin_fails_serve_extra_check
    tests/gates_suite/test_protocol.py
      ::TestProtocolSummaryGate::test_real_repo_scan_runs_end_to_end_without_crashing
    tests/gates_suite/test_waive.py
      ::TestDsl001::test_docarch001_wiring_comment_does_not_self_match
    tests/test_registry_exhaustiveness.py
      ::TestArchChecksReg008BurnDown::test_no_reg008_findings_for_arch_checks_yaml
      ::TestSystemDesignReg008BurnDown::test_no_reg008_findings_for_system_design_yaml
      ::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
      ::TestComplianceReg008BurnDown::test_no_reg008_findings_for_compliance_yaml
    tests/test_waive_gate.py
      ::TestWaive006RealRepo::test_zero_errors_on_real_repo

    plus, worker died with no timeout dump, suspected OOM, never rescheduled:
    tests/system/test_frob_self_model.py
      ::TestFrobSelfModel::test_fragments_module_fs_read_is_declared_not_selfaudit001
      ::TestFrobSelfModel::test_check_admission_exec_sites_are_declared_not_selfaudit001

TRIAGE THEM BY SHAPE BEFORE FIXING ANY OF THEM. At least three distinct kinds are
mixed here and they want different work:

  SELF-SCAN TESTS THAT ASSERT THE REPO IS CLEAN. The protocol real-repo scan, the
  four registry burn-down tests, and the WAIVE006 zero-errors-on-real-repo test
  all measure THIS REPOSITORY rather than a fixture. They go red when the repo
  accumulates findings, which means they are burn-down counters, not regressions.
  Determine for each whether the finding count grew because of a landed change
  (a real regression) or because these are ratchets that were already behind (a
  debt to burn). Do not "fix" a ratchet by loosening it.

  THE TWO ARTIFACT-SMOKE FAILURES ARE PROBABLY NOT NEW. Two artifact-smoke
  failures appeared in the very first ubuntu run examined during this drive,
  before any of the recent batch landed. Check that history before attributing
  them to anything recent -- this repo has a recorded incident of five of six
  "new" identities in a sweep-filed ticket turning out to be pre-existing.

  THE TWO WORKER DEATHS ARE NOT TEST FAILURES YET. A worker that dies with no
  timeout dump, under measured memory pressure, is an unmeasured test, not a
  failing one. Re-run those two alone on a quiet machine before concluding
  anything about them. If they pass in isolation, the finding is about our own
  fleet's memory ceiling, not about those tests.

WHAT TO DO
  1. Re-run the full suite ONCE on as quiet a machine as can be arranged, with
     enough worker headroom that the scheduler does not abort, and record the
     COMPLETE failing set. Everything below depends on having a real denominator.
  2. Classify every failure as regression, pre-existing debt, or unmeasured.
  3. Fix the regressions. File the debt with counts. Re-measure the unmeasured.
  4. Do NOT loosen a self-scan assertion to reach green. Those tests are the only
     thing standing between this repo and the "our own green is evidence of
     nothing" failure it keeps finding in consumers.

MUST-FIRE FIXTURE:   a complete full-suite run finishes without a scheduler abort
                     and reports its failing set as COMPLETE rather than partial.
MUST-STAY-QUIET:     the 6419 unit tests stay at zero failures.
THIRD FIXTURE:       each self-scan test that is retained still fails when a real
                     finding of its kind is introduced -- proven by introducing
                     one, not assumed.

ACCEPTANCE
- A complete, non-aborted full-suite run recorded, with its failing set.
- Every failure classified regression / pre-existing / unmeasured, with evidence.
- No self-scan assertion loosened to reach green.
- The two suspected-OOM tests re-measured in isolation.
- All three fixtures committed.
