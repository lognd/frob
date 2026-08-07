---
id: T-1287
title: 'TEST005 burn-down: src/frob/serve (32 findings, 3 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/serve/**
- tests/serve/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_serve.py::TestBuildServer::test_registers_all_five_tools
- tests/test_serve.py::TestBuildServer::test_require_mcp_raises_when_unavailable
- tests/test_serve_daemon.py::TestPollRebaseBot::test_conflicting_branch_warns
- tests/test_serve_daemon.py::TestPollRebaseBot::test_clean_branch_no_warning
designated_repro_test: null
acceptance:
- text: GIVEN the serve package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/serve/**
  evidence:
  - tests/test_serve.py::TestBuildServer::test_registers_all_five_tools
  - tests/test_serve.py::TestBuildServer::test_require_mcp_raises_when_unavailable
  - tests/test_serve_daemon.py::TestPollRebaseBot::test_conflicting_branch_warns
  - tests/test_serve_daemon.py::TestPollRebaseBot::test_clean_branch_no_warning
- text: GIVEN a 0.0%-branch symbol in serve WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/test_serve.py::TestBuildServer::test_registers_all_five_tools
- text: GIVEN a new test added to close a serve TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/test_serve.py::TestBuildServer::test_registers_all_five_tools
  - tests/test_serve.py::TestBuildServer::test_require_mcp_raises_when_unavailable
  - tests/test_serve_daemon.py::TestPollRebaseBot::test_conflicting_branch_warns
  - tests/test_serve_daemon.py::TestPollRebaseBot::test_clean_branch_no_warning
threat: null
component: null
---
Package: src/frob/serve (or the listed root modules).
TEST005 findings at current baseline: 32 total, 3 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
_daemon.py :: daemon_status
server.py :: build_server
server.py :: run_stdio

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.