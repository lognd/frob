---
id: T-3757
title: 'win32 suite aborts: raise per-test timeout so slow full-repo-scan gate tests
  do not crash their worker'
state: done
kind: bug
origin: human
created: '2026-09-04'
priority: medium
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
evidence:
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_win32_test_step_raises_per_test_timeout_to_600
designated_repro_test: null
evidence_changes:
- old_node: cmd:uv run python -m pytest tests/test_ci_workflow_matrix.py tests/unit/test_release_workflow_gate.py
    -p no:xdist -q exit=0 sha256=b45c62f1acf0
  new_node: tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_win32_test_step_raises_per_test_timeout_to_600
  reason: T-3757 win32 timeout=600 change needs pytest node-id evidence for a code-kind
    ticket; the CI-config cmd-evidence is invalid per COV003, replaced with the T-3771
    regression test that asserts --timeout=600 in ci.yml
  actor: logan
  at: '2026-09-04'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
PROBLEM: the win32 CI leg (advisory, continue-on-error) cannot run to completion because a CLASS of slow full-repo-scan GATE tests exceed the default 120s per-test timeout on the slow Windows runner, os._exit-kill their xdist worker, and the worker crash aborts the whole suite (T-3608 stall-abort) -- so we never get the full failing-test list needed to drain the remaining ~198 win32 failures. Observed crashers: tests/system/test_fleet_status_ticket_readiness_arch001.py, tests/test_docptr_gate.py (both already skipif'd in T-3754), and tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive. There will be MORE in this class.

FIX: raise the win32 Test step's default per-test timeout from 120s to 600s by appending --timeout=600 to the pytest invocation's ArgumentList in .github/workflows/ci.yml (line ~1591). pyproject addopts sets --timeout=120; a second --timeout=600 on the command line wins (pytest-timeout/argparse last-value wins, verified locally: uv run python -m pytest tests/unit/test_config.py -q -p no:xdist --timeout=1 --timeout=300 does NOT error at 1s). The self-scan-heavy tests keep their own @pytest.mark.timeout(1200) marker (marker > CLI). Do NOT touch ubuntu or macos Test steps.