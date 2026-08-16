---
id: T-2181
title: 'T-2179 residue: ''already implemented'' still decides from scope-file overlap,
  so any branch that touched a shared file claims someone else''s ticket -- t-2107
  and t2049-series falsely claim T-2114'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_scope_touch_in_a_different_commit_is_not_correlated
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_finds_a_branch_with_unlanded_commits
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_empty_when_nothing_touches_it
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_ledger_only_churn_is_not_reported
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_empty_scope_globs_never_reports
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_scope_touch_in_a_different_commit_is_not_correlated
threat: null
component: null
anchor: false
anchor_reason: null
---
