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
sprint: v0.531.0
runs_last: false
milestone: 0.531.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'retracts this ticket''s premise against a CI measurement: 0 failures across
    13610 tests on an unloaded machine, versus 9 locally. Six of the nine were self-scan
    tests reading this checkout''s ~20 agent worktrees and two were memory-induced
    worker deaths; records the standing rule that self-scan behaviour is measured
    where the tree is clean, and narrows the remaining work to excluding nested worktrees
    from those tests'
  actor: logan
  at: '2026-09-07'
  old_length: 5009
  new_length: 7907
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

CORRECTION, MEASURED ON CI 2026-09-07: NONE OF THE NINE REPRODUCE. This ticket's
premise above is wrong and is left in place only as the record of what a loaded
machine reported. The authoritative measurement is CI run 34091766127, ubuntu
leg, on the same tree plus the two regression fixes:

    SUITE-RESULT: exitstatus=0 collected=13610 failed=0

Zero test failures across 13610 tests. macOS's suite step also passed. Both legs'
JOBS still failed, but on a later step (`frob check` self-gate, 8 errors) which
is now tracked separately as T-4145 -- not on any test.

WHY THE LOCAL RUN SAW NINE AND CI SAW ZERO, which is the durable lesson and the
reason this correction is worth more than the retraction:

  SIX OF THE NINE WERE SELF-SCAN TESTS -- the protocol real-repo scan, the four
  registry burn-downs, and the zero-errors-on-real-repo waiver test. Those
  measure THIS CHECKOUT rather than a fixture. This checkout carries roughly
  twenty agent worktrees under the agent-config directory that CI does not have,
  each holding a different branch's files. A test that scans "the repository"
  here is scanning twenty overlapping trees.

  THE TWO WORKER DEATHS WERE MEMORY, NOT CODE. They died with no timeout dump
  while the machine was measured at high load with swap in use, exactly as the
  ticket suspected. CI, unloaded, ran them.

SO THE STANDING RULE IS: MEASURE SELF-SCAN BEHAVIOUR WHERE THE TREE IS CLEAN.
A local full-suite result on a coordinator machine running a fleet is not
evidence about the repository; it is evidence about the fleet. This is the same
nested-worktree contamination a consumer already reported from the other side --
their checkout's type stage scanned agent worktrees and reported unresolved
imports for files that exist only on other branches, and they had to exclude the
directory in three separate config files. We have now hit the identical class in
our own test suite without recognising it for what it was.

WHAT REMAINS OF THIS TICKET. The acceptance criteria still stand, but the work is
smaller and different than filed:
  - A complete, non-aborted full-suite run: ACHIEVED, on CI. Record CI as the
    place that measurement happens, not this machine.
  - Classify every failure: DONE by this correction -- all nine were environmental,
    none were regressions or debt.
  - Do not loosen self-scan assertions: still binding, and now more clearly right.
    Had anyone "fixed" those six by weakening them, they would have destroyed
    real checks to satisfy a measurement artefact.
The residual work worth keeping is the LAST acceptance criterion only: prove each
retained self-scan test still fails when a real finding of its kind is
introduced, and additionally make those tests either skip or exclude nested agent
worktrees so a local run is meaningful again. That second half is the same fix a
consumer asked for and is worth doing here.
