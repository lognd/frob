---
id: T-2815
title: 'Reformat batch 15/N: 10 files pending ruff-format (T-2359 child)'
state: done
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: T-2359
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_check_budget.py
- tests/unit/test_ticket_close_bug002_t1438.py
- tests/unit/test_ticket_new_related.py
- tests/unit/test_ticket_runner_ledger_mirror.py
- tests/unit/test_ticket_runner_ledger_verbs_export_t2647.py
- tests/unit/test_tickets_evidence_only_scope.py
- tests/unit/test_unlanded_branch_work.py
- tests/unit/test_waive_audit_watermark.py
- tests/unit/verify/test_drain.py
- tests/unit/verify/test_quarantine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_check_budget.py::TestSelectBudgetChunks::test_greedy_pack_fits_under_budget
- tests/unit/verify/test_drain.py::TestRunDrainAsync::test_declines_while_a_land_is_in_progress
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: ac2d4ae3dd62b421817b30b082117a2bfa4cf48a
---
Batch 15 of the T-2359 ruff-format-only reformat epic. 10 files re-measured against current main via ruff format --check (20 files remaining before this batch). Format-only, no semantic changes. Excludes T-2373 historically-claimed test_ticket_land.py test_ticket_work_and_land_finish.py test_tickets_organization.py test_tickets_priority.py unit/test_app_runners_batch6.py unit/test_app_runners_t2395_contention.py (per standing guidance, even as its lease scope has now changed); T-2373 currently-live test_ticket_new_priority_inherit_t1960.py test_waive_audit_runner.py verify/test_backpressure.py (its lease now reads non-empty and includes these); T-2806 tests/unit/test_check.py (actively landing right now per fleet_status.py)