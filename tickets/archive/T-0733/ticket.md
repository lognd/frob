---
id: T-0733
title: 'daemon continuous verification: post-land re-verify + rebase-bot advance warning
  for in-flight worktrees'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: high
parent: T-0177
tier: ticket
sprint: null
scope:
- src/frob/serve/**
- src/frob/graph/**
- docs/modules/serve.md
- tests/test_serve_daemon.py
- tests/test_serve.py
- pyproject.toml
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_serve_daemon.py
  reason: unit tests for the T-0733 daemon background jobs (post-land re-verify, rebase-bot)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/test_serve.py
  reason: existing TestBuildServer.test_registers_all_five_tools asserts the exact
    registered-tool-name set; T-0733 adds frob_daemon_status, so the assertion needs
    updating
  actor: logan
  at: '2026-07-22'
- op: add
  glob: pyproject.toml
  reason: 'REL001 fix per coordinator/reviewer instruction: bump version to 0.97.0
    for new public API in src/frob/serve/_daemon.py and run frob release stamp'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: .frob-release.json
  reason: 'REL001 fix per coordinator/reviewer instruction: bump version to 0.97.0
    for new public API in src/frob/serve/_daemon.py and run frob release stamp'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: 'REL001 fix per coordinator/reviewer instruction: bump version to 0.97.0
    for new public API in src/frob/serve/_daemon.py and run frob release stamp'
  actor: logan
  at: '2026-07-22'
evidence:
- tests/test_serve_daemon.py::TestPollPostLand::test_head_unchanged_is_noop
- tests/test_serve_daemon.py::TestPollPostLand::test_head_moved_refreshes_verdict
- tests/test_serve_daemon.py::TestPollRebaseBot::test_no_leases_is_no_warnings
- tests/test_serve_daemon.py::TestPollRebaseBot::test_conflicting_branch_warns
- tests/test_serve_daemon.py::TestPollRebaseBot::test_clean_branch_no_warning
- tests/test_serve_daemon.py::TestFrobDaemonStatus::test_reads_current_status
- tests/test_serve_daemon.py::TestRunDaemonCycle::test_runs_both_jobs_and_returns_status
- tests/test_serve_daemon.py::TestStartDaemon::test_background_loop_runs_a_cycle_then_stops
- tests/test_serve.py::TestBuildServer::test_registers_all_five_tools
designated_repro_test: null
acceptance:
- text: GIVEN a land on main WHEN the daemon is running THEN a fresh delta verdict
    is available via MCP within a minute without any agent invoking frob check; GIVEN
    an in-flight worktree whose eventual land would conflict THEN a warning is published
    before the agents Done report
  evidence:
  - tests/test_serve_daemon.py::TestPollPostLand::test_head_moved_refreshes_verdict
  - tests/test_serve_daemon.py::TestPollRebaseBot::test_conflicting_branch_warns
threat: null
component: null
---
User directive 2026-07-22: the serve daemon (T-0177 warm state, frob_check_delta) should run continuously so agents and the coordinator never wait on verification. Two jobs: (1) POST-LAND RE-VERIFY: after each land (file-watch on main HEAD), refresh warm state and run the delta + touched-set tests once, exposing the result via an MCP tool/status file so the coordinators land verification is a lookup; (2) REBASE-BOT: for each active worktree branch (enumerate .claude/worktrees + live leases), periodically merge current main in a SCRATCH copy, run the delta, and publish conflict/baseline-drift warnings BEFORE the agent finishes -- converting the main-moved penalty (the sessions No.1 churn source) into advance notice. PREREQ: T-0581 process-pool deadlock fix before trusting continuous check load (pytest-timeout contains test-side blast radius meanwhile); coordinate with T-0602 (per-obligation incremental) but do not block on it.