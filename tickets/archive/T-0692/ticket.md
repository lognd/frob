---
id: T-0692
title: 'CI hardening: per-test timeout so a deadlocked test fails in minutes, not
  the 6h job cap'
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- pyproject.toml
- Makefile
- docs/guides/**
- uv.lock
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: uv.lock
  reason: pytest-timeout added to the dev dependency group requires the lockfile to
    move in the same commit
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/integration/test_interfaces.py
  reason: 'config-only ticket: evidence is the sanctioned CLI-dispatch integration
    test (playbook section 5); close requires it in scope'
  actor: logan
  at: '2026-07-22'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: GIVEN a test that deadlocks WHEN the suite runs in CI THEN that test fails
    with a timeout naming it within minutes and the run completes; GIVEN the known-slow
    system tests THEN they pass under their explicit overrides
  evidence: []
threat: null
component: null
---
Field evidence 2026-07-22: the CI Test job ran 5h59m30s before cancellation at the 6h cap -- a deadlock, not slow tests. Same hang reproduced locally three ways: TestRunGatesDelta exit-143 timeouts on unmodified main, and TWO zombie pytest trees from dead worktree sessions (12h53m and 10h09m old) wedged inside frob check subprocess tests, swept this session. Root cause class: _run_combined_jobs forks a ProcessPoolExecutor inside an active ThreadPoolExecutor (disclosed in T-0265's Done report; T-0581's process-pool redesign is the structural fix and should be treated as HIGH priority). This ticket is the harness guard: add pytest-timeout (per-test ceiling ~120s, thread method) to the test dependency group and addopts, so any future deadlock fails the one test in minutes and CI reports a named culprit instead of burning the job cap; document the interplay in the testing guide. Keep the ceiling generous enough for the known-slow system tests or mark those with explicit timeout overrides.