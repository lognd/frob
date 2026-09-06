---
id: T-4066
title: 'F-load: xdist-load-sensitive flake population beyond the daemon tests (test_ticket_runner_archive_force,
  test_check_runner, test_check_tool_unavailable, test_docptr_gate/test_artifact_smoke
  clusters)'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_runner_archive_force.py
- tests/test_check_runner.py
- tests/unit/test_check_tool_unavailable.py
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
found while working T-4055.

CI-history mining (gh api on 23 recent ubuntu-latest CI job logs, via SUITE-RESULT/SUITE-RESULT-FAILED markers in each job's log) surfaced MORE than the 3 tests named in T-4055's own body. Full enumeration, one row per (run, failing test):

TRUE single-run intermittent failures (different test each occurrence, passes on adjacent commits) -- same load-sensitive-population shape as the two daemon tests fixed under T-4055:
  run 34030362843  tests/test_serve_socket.py::TestRunSocketDaemon::test_serves_one_request_then_idle_exits   (fixed under T-4055)
  run 33739420656  tests/test_serve_socket.py::TestRunSocketDaemon::test_stale_socket_file_is_replaced        (fixed under T-4055; also DROPPED an existing @pytest.mark.flaky(reruns=2) that was masking it -- reruns are prohibited by this repo's own doctrine)
  run 34019760758  tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring::test_capability_conformance_fires_through_real_gate_dispatch  (already fixed, T-4018/T-4047)
  run 34019848542  tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal
  run 34024645783  tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_with_no_live_leases_stays_quiet
  run 33890430001  tests/test_check_runner.py::TestApplyTierAAndReverify::test_ticket_scoped_fix_never_touches_files_outside_declared_scope

NOT YET CLASSIFIED (only sampled from log text, not locally reproduced or root-caused -- that is this new ticket's job):
  run 33945397250  7 tests all in tests/unit/test_check_tool_unavailable.py failed TOGETHER in one run (TestTyUnavailable, TestRuffUnavailable x2, TestCargoUnavailable x3, TestCheckResultRendersUnavailableTool) -- all-together-in-one-run points at a SHARED RESOURCE under xdist (a PATH-mocking fixture, or a single stubbed binary directory two workers raced on), not independent wall-clock bets. Worth checking first per T-4055's classification framework.

SEPARATELY: runs 34005559354 through 34013571660 (5 consecutive ubuntu CI runs) show a REPEATING, non-flaky-shaped cluster (tests/system/test_artifact_smoke.py x2, tests/test_docptr_gate.py, tests/test_ticket_land_proof_claims.py x6, tests/test_ticket_runner_archive_force.py::test_force_overrides_the_live_lease_refusal) that fails IDENTICALLY across consecutive commits then stops appearing from 34019760758 onward. That is shaped like a real bug that existed for a window and was fixed by a later commit, not scheduler-driven flakiness -- flagging here for the record but it does NOT belong in the same population as this ticket's flake list; do not spend flake-remediation effort on it unless CI history shows it recurring again.

Sampling method: gh api repos/{owner}/{repo}/actions/jobs/<id>/logs on the ubuntu-latest job of the last 23 CI runs (push+pull_request, both failure and success conclusions) on main, grepping the SUITE-RESULT/SUITE-RESULT-FAILED markers tests/conftest.py already emits. This is CI-history mining, not a local repro -- classification (wall-clock bet vs shared xdist resource vs order dependence) and any fix for the archive_force/check_runner/check_tool_unavailable tests is this ticket's own scope, per T-4055's own instruction not to expand its declared scope (tests/test_serve_socket.py) to cover them.