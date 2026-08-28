---
id: T-3247
title: Whole-repo-scan tests exceed the 120s per-test cap, killing the xdist worker
  and aborting the whole suite (root cause of the ubuntu hang)
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
- pyproject.toml
- tests/system/test_frob_self_model.py
- tests/unit/strata/test_selfconform.py
- tests/system/test_fleet_status_ticket_readiness_arch001.py
- tests/gates/test_scan_timeout_enforcement.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/system/test_frob_self_model.py
  reason: 'the pyproject-only scope drew a plausibility warning correctly: the timeout
    overrides must be written into the whole-repo-scan test files themselves, which
    is where the fix actually lands'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: 'the pyproject-only scope drew a plausibility warning correctly: the timeout
    overrides must be written into the whole-repo-scan test files themselves, which
    is where the fix actually lands'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/system/test_fleet_status_ticket_readiness_arch001.py
  reason: 'the pyproject-only scope drew a plausibility warning correctly: the timeout
    overrides must be written into the whole-repo-scan test files themselves, which
    is where the fix actually lands'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/gates/test_scan_timeout_enforcement.py
  reason: T-3247's enforcement gate is implemented as a self-contained repo test (AST/import-based
    whole-repo-scan detector) rather than a frob-check gate rule, because src/frob/gates/__init__.py
    is under a live T-3196 scope lease and cannot be edited
  actor: logan
  at: '2026-08-28'
evidence:
- tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations::test_must_fire_on_unmarked_whole_repo_scan_call
- tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations::test_must_stay_quiet_on_ordinary_fast_test
- tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations::test_must_stay_quiet_when_method_level_override_present
- tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations::test_must_stay_quiet_when_class_level_pytestmark_present
- tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations::test_must_stay_quiet_on_synthetic_repo_fixture_test
- tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations::test_must_stay_quiet_on_synthetic_tmp_path_target
- tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations::test_must_stay_quiet_on_run_call_with_explicit_path_argument
- tests/gates/test_scan_timeout_enforcement.py::TestRepoIsScanTimeoutClean::test_no_unmarked_whole_repo_scan_tests_in_repo
- tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED from the CI run of 2026-08-28. This is the ROOT CAUSE of the ubuntu
"hang" and of the windows INTERNALERROR. Both platforms show the same chain.

THE CHAIN, in order:

  1. `pyproject.toml:218-219` sets `faulthandler_timeout = 100` and
     `addopts = "-q -n auto --dist=loadgroup --timeout=120 --timeout-method=thread"`.
     So: stack dump at 100s, kill at 120s, per test.

  2. Several tests perform a WHOLE-REPO SCAN and legitimately exceed 120s on
     CI's small runners. The faulthandler dumps name them precisely:
       ubuntu: tests/system/test_frob_self_model.py:502
                 test_sys_gate_zero_violations
                 -> build_graph -> _ingest_source_files -> parse_file
       ubuntu: tests/system/test_fleet_status_ticket_readiness_arch001.py:20
                 -> subprocess.communicate
       windows: tests/unit/strata/test_selfconform.py:1235
                 test_repo_design_and_declarations_are_self_conformant
                 -> check_self_conformance -> _collect_sys_violations
                 -> scan_file_capabilities -> _python_resolved_candidates

  3. `--timeout-method=thread` kills the xdist WORKER, not just the test.
     Output shows `[gw0] node down: Not properly terminated`.

  4. xdist's loadscope scheduler then crashes on the dead worker:
       INTERNALERROR> File "xdist/scheduler/loadscope.py", line 275,
                        in _assign_work_unit
       INTERNALERROR>   worker_collection = self.registered_collections[node]
       INTERNALERROR> KeyError: <WorkerController gw6>

  5. The whole session aborts with exitstatus=3, discarding the real results.

THESE ARE NOT DEADLOCKS. They are slow tests hitting a cap. The repo's own
profiling already sized this: `_python_resolved_candidates`' docstring records
"2448 calls over 1224 files, 94.25s of a 111.09s isolated scan_file_capabilities
sweep" (T-2798) -- and that is the number AFTER T-2798's optimization. A
whole-repo capability scan is inherently near the 120s cap on a fast machine and
over it on a CI runner.

THE ACCOUNTABILITY HOLE. `pyproject.toml:202` already documents that slow tests
"need their own `@pytest.mark.timeout(N)` override -- see
docs/guides/testing.md#per-test-timeout-ci-hardening for the list". That
mechanism EXISTS and is DOCUMENTED. Measured just now, only FOUR test files in
the entire repo carry a `mark.timeout`:

    tests/system/test_natives_build_integration.py
    tests/system/test_scaffold_dx.py
    tests/test_gates_fix_engine.py
    tests/test_gates_suppress.py

None of the three whole-repo-scan tests above is among them. The rule lives in
prose in a docs page and a config comment, and prose is not enforced -- which is
a failure mode this repo has hit repeatedly.

DO NOT FIX THIS BY RAISING THE GLOBAL TIMEOUT. The 120s cap is what makes a
genuine deadlock fail fast instead of wedging CI; raising it globally trades a
real guard for convenience and re-creates the manual-cancellation history
T-3192 was built to end. Do not disable `--timeout-method=thread` either
without understanding why it was chosen (a signal-based method does not
interrupt a blocked C call).

WHAT TO BUILD:
  1. Enumerate every test that performs a whole-repo scan (graph build, self-
     conformance, capability sweep, full `frob check` spawn). State the method
     used to enumerate -- a hand list will rot.
  2. Give each a justified `@pytest.mark.timeout(N)` with N derived from a
     MEASUREMENT on the slowest supported runner, not a guess.
  3. GATE IT. A test that performs a whole-repo scan without an explicit
     timeout override must be a finding, so the next such test cannot be added
     silently. That is the difference between fixing these three and fixing the
     class. Per the standing directive, the detector must match on SYMBOLS via
     the parser, never on substrings.
  4. Separately: a killed worker crashing the scheduler (step 4) turns N test
     failures into a total suite abort. Determine whether `--dist=loadgroup` can
     survive a worker death, or whether this is an upstream xdist defect worth
     pinning/working around. Report; do not paper over it.

MUST-FIRE FIXTURE: a whole-repo-scan test with no timeout override is flagged.
MUST-STAY-QUIET FIXTURE: an ordinary fast unit test is not flagged, and a
whole-repo-scan test that HAS a justified override is not flagged.

RELATED, VERIFY BEFORE ASSUMING IT IS THE SAME BUG: the same CI run failed
`tests/system/test_ci_hang_guard_positive_control.py::TestCiHangGuardPositive
Control::test_ordinary_fast_test_is_unaffected`. That is T-3192's OWN positive
control for the hang guard. A hang guard whose control fails is unproven. It may
be collateral from the abort or an independent defect -- determine which and say
so with evidence. If independent, file it separately rather than folding it in.