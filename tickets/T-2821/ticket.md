---
id: T-2821
title: 'Reformat batch 16/N: 12 files pending ruff-format (T-2359 child)'
state: queued
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
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
- tests/test_ticket_work_and_land_finish.py
- tests/test_tickets_organization.py
- tests/test_tickets_priority.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_app_runners_t2395_contention.py
- tests/unit/test_capability_native.py
- tests/unit/test_check.py
- tests/unit/test_wait_for_land_slot_unattributed.py
- tests/unit/test_waive_audit_runner.py
- tests/unit/verify/test_backpressure.py
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
Batch 16 of the T-2359 ruff-format-only reformat epic. Fresh uv run ruff format --check . measured 13 files pending (up from the 10 batch-15 assumed, since new content landed since: T-2807/T-2817/T-2818/T-2800 work). Excludes tests/unit/test_coordinator_scripts.py, currently live-claimed by T-2818 (in-progress). Format-only, no semantic changes, no fixture-corpus files.