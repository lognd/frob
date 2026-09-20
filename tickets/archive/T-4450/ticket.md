---
id: T-4450
title: 'CI self-gate must collect fresh: wipe the Test step''s collection cache and
  dump diagnostics before frob check (Windows COV003 x56)'
state: done
kind: bug
origin: agent
created: '2026-09-12'
priority: critical
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/test_ci_workflow*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4450: document the BUG002 waiver for this CI-config-only change, per
    the T-4372/T-3785-era waiver-comment precedent in ci.yml itself'
  actor: logan
  at: '2026-09-12'
  old_length: 2174
  new_length: 2674
evidence:
- tests/test_ci_workflow_matrix.py::TestSelfGateCollectsFresh::test_diagnostics_step_exists_and_precedes_self_gate
- tests/test_ci_workflow_matrix.py::TestSelfGateCollectsFresh::test_diagnostics_step_runs_on_all_three_legs
- tests/test_ci_workflow_matrix.py::TestSelfGateCollectsFresh::test_diagnostics_step_wipes_collection_caches_not_coverage_state
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Windows self-gate has reported 56 COV003 + 2 TEST002 errors on the two POSIX-only stackdump test modules on every run since 2026-09-09, through T-4429, T-4408 and T-4447 (which each measured correct on the winrun mirror, cold and warm). Two investigation passes (T-4444, T-4449 and an investigator agent, findings in the T-4449 fail log) could not reproduce the runner's state: the mirror cannot finish the full suite before the self-gate (xdist workers die under remote PowerShell, or the 6000s budget hits at 17%). The runner-only difference is that the self-gate runs AFTER the full Test step in the same checkout, and the investigator DID observe that stale .frob/ state from an earlier session yields 129 COV003 + 38 TEST002 on the mirror until .frob/ is wiped -- i.e. a leftover collection artifact is enough to produce exactly this class of error. Two changes to .github/workflows/ci.yml, both legs: (1) DIAGNOSE on the runner: before the self-gate, print the .frob/ listing, the size and top-level keys of .frob/pytest-collect.json (if present) and `python -c "from frob.testing._collect import collect_python_tests; ..."` platform_skipped for the root, so the next Windows run names the poisoned artifact directly; (2) MEASURE THE TREE, NOT THE TEST STEP'S RESIDUE: delete .frob/pytest-collect.json (and any other collection cache the Test step can leave: cargo-collect.json etc.; keep .frob/coverage-stamp and .frob/baseline per T-1265) immediately before `uv run frob check` so the self-gate performs a fresh collection exactly like the mirror measurement that gives 0 errors. Keep tests/test_ci_workflow_matrix.py (and any ci.yml assertion tests) green: add assertions that the self-gate step is preceded by the cache wipe. ACCEPTANCE: (1) the next Windows run's log shows the diagnostic block; (2) Windows self-gate COV/TEST rows report 0 errors for tests/unit/test_conftest_stackdump.py, tests/unit/test_stackdump.py and src/frob/testing/_stackdump.py; (3) ubuntu/macOS self-gates unchanged. Sprint v0.531.0 (CI green blocker). Related: T-4449 (root cause still open; this ticket makes CI measure correctly and captures the evidence the root-cause fix needs).


frob:waive BUG002 reason="CI-config change (.github/workflows/ci.yml self-gate diagnostics/cache-wipe step); the fix's effect (fresh collection avoiding stale .frob/*-collect.json) is only measurable on the real GitHub Actions Windows runner in the same job as the full Test step -- the T-4449 investigation could not complete a full-suite run on the winrun mirror (xdist worker deaths, injected-Ctrl-C-class subprocess failures under remote PowerShell) to reproduce that exact sequencing locally."