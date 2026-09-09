---
id: T-4374
title: Bare pytest argv in worker-crash-retry test unresolvable on macOS xdist worker
state: queued
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
tests/test_coverage.py::TestWorkerCrashRetryRealSubprocessRecoversFromAddopts::test_real_pytest_subprocess_recovers_and_produces_coverage_xml
fails on macOS CI (run 34358765772) with assert 3 == 0. Log shows:

  ERROR ... watchdog spawn of ['pytest', '--cov=.', '--cov-report=', 'test_widget.py', '-p', 'no:xdist', ...] failed: [Errno 2] No such file or directory: 'pytest'
  ERROR ... serial retry after worker-crash also failed to complete (the wall-clock deadline was exceeded)

The test calls _refresh_mod._retry_after_worker_crash directly with a
bare ["pytest", ...] argv (not resolved via project_tool_argv, since
production callers always build argv through _pytest_argv which already
uses project_tool_argv -- confirmed by reading _run_full_suite /
_run_incremental_or_restamp, the only two real callers of
_pytest_outcome / _retry_after_worker_crash). Bare "pytest" relies on
PATH resolution reaching a deeply nested xdist-worker subprocess-of-
subprocess on macOS, which T-4368's PATH export does not guarantee
reaches that deep (measured: passes locally on Linux where the outer
venv's PATH propagates fine).

Precedent immediately below in the same file:
TestNeutralizedAddoptsPytest11Entrypoint's
test_p_no_xdist_on_cli_no_longer_needs_a_manual_addopts_override uses
[sys.executable, "-m", "pytest", ...] specifically to avoid PATH lookup.
Same class of defect T-4369 fixed for mutation evidence.

Plan: change the failing test's _retry_after_worker_crash call site to
pass [sys.executable, "-m", "pytest", "--cov=.", "--cov-report=", "-n",
"4", "test_widget.py"] instead of bare ["pytest", ...]. Test-only fix --
production argv is already resolved via project_tool_argv and
unaffected. No change needed in src/frob/testing/_coverage_refresh.py.

Verify: uv run pytest tests/test_coverage.py::TestWorkerCrashRetryRealSubprocessRecoversFromAddopts::test_real_pytest_subprocess_recovers_and_produces_coverage_xml -x -q