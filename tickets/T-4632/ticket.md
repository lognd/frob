---
id: T-4632
title: Clean tests/unit docstrings of change-narrative (DOCARCH001) cluster 1
state: queued
kind: docs
origin: human
created: '2026-09-19'
priority: medium
parent: T-4419
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/coordinator_suite/test_fleet_worktrees.py
- tests/unit/test_app_runners_batch7.py
- tests/unit/test_check_budget.py
- tests/unit/test_ticket_runner_ledger_mirror.py
- tests/unit/test_ticket_store.py
- tests/unit/graph/test_dsl_markdown_waive.py
- tests/unit/rapid_sweep_suite/test_filing.py
- tests/unit/rapid_sweep_suite/test_sweep_run.py
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: Given a scoped frob check on cluster 1 files, when DOCARCH001 is measured,
    then its finding count for those files is 0
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-4419 (166->182 re-measurement, 2026-09-19). Cluster 1: 32 DOCARCH001 findings across 9 files. Rewrite each flagged docstring to state WHAT the test proves, not the change narrative. See T-4419 body for the full per-file breakdown and cluster plan.