---
id: T-2127
title: 'Terminal-state work strands in unlanded worktrees: closed/dropped/failed tickets
  read as queued on main, and doable reports 113 such branches while sweep marks exactly
  those removable'
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_query.py
- tests/unit/test_app_runners_doable_stale_lease.py
evidence_scope:
- tests/unit/test_app_runners_doable_stale_lease.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_runners_doable_stale_lease.py
  reason: test evidence for the T-2127 doable unlanded-branch-scan cache fix
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_second_call_within_ttl_reuses_the_cache_not_a_fresh_scan
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_expired_cache_is_ignored
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_fresh_cache_round_trips
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_unlanded_branch_is_summarized
designated_repro_test: tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_second_call_within_ttl_reuses_the_cache_not_a_fresh_scan
threat: null
component: null
anchor: false
anchor_reason: null
---
