---
id: T-3621
title: 'ubuntu-only run 33459475864 triage: 3 failing tests'
state: in-progress
kind: bug
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_check.py
- tests/test_ticket_runner_archive_force.py
- tests/unit/test_graph_build_lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'declare no-behavior-change: triage found none of the 3 failures reproduce
    on current main'
  actor: logan
  at: '2026-08-31'
  old_length: 1241
  new_length: 1494
evidence:
- tests/system/test_cli_check.py::TestCheckPolyglot::test_pinned_check_type_reports_skipped_line
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal
- tests/unit/test_graph_build_lock.py::TestBuildGraphLockScope::test_two_processes_never_commit_to_the_same_cache_concurrently
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33459475864 ubuntu, 3 remaining failures (each: REPRODUCE FIRST,
then fix or report false-premise/flaky with evidence):

1. tests/system/test_cli_check.py::TestCheckPolyglot::
   test_pinned_check_type_reports_skipped_line -- possibly affected by
   recent capability/lang_project changes (T-3527 touched project
   surface docs; T-3605 touched scaffold tests). Reproduce with
   -p no:xdist and with xdist to separate order-dependence from a real
   break.

2. tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI
   ::test_force_overrides_the_live_lease_refusal -- the T-3578
   archive-force area (diagnostics landed earlier; root cause still
   open). If the failure's git stderr shows the T-3578 signature,
   append the evidence to T-3578 and fix here if in reach.

3. tests/unit/test_graph_build_lock.py::TestBuildGraphLockScope::
   test_two_processes_never_commit_to_the_same_cache_concurrently --
   NOTE: T-3607 (cache rebuild rename-quarantine fix) landed AFTER the
   measured run's sha, so first check whether current main still fails
   this test at all; T-3607 changed _recreate's locking, which may fix
   OR conflict with this test's contract. Run it 3x against current
   main before touching anything.

frob:no-behavior-change reason="triage-only ticket: reproduced each of the 3 named ubuntu failures against current main and none failed (test 3 fixed upstream by T-3607, tests 1/2 did not reproduce as flakes/order-dependence); no code change was made"