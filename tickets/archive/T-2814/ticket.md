---
id: T-2814
title: 'Reformat batch 14/N: 13 files pending ruff-format (T-2359 child)'
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
- tests/unit/dup/test_type_name_only_regression_t1957.py
- tests/unit/strata/test_waive.py
- tests/unit/test_app_runners.py
- tests/unit/test_app_runners_batch7.py
- tests/unit/test_app_runners_t0976_mutation_evidence.py
- tests/unit/test_app_runners_t1822_already_landed.py
- tests/unit/test_app_sys_capacity.py
- tests/unit/test_app_sys_threats.py
- tests/unit/test_app_sys_trace.py
- tests/unit/test_lang_primitives.py
- tests/unit/test_lang_strata.py
- tests/unit/test_new_ticket_scope_overlap_warning.py
- tests/unit/test_ticket_close_bug002_t1427.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/dup/test_type_name_only_regression_t1957.py::TestTypeNameOnlyCloneMissedByDefault::test_default_config_does_not_catch_the_function_pair
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_no_population_reports_current_violations
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 52e7664b63b979c31f1821cac6dc978ce522c6ee
---
Batch 14 of the T-2359 ruff-format-only reformat epic. 13 files re-measured against current main via ruff format --check (32 files remaining before this batch). Format-only, no semantic changes. Excludes T-2373 historically-claimed test_ticket_land.py test_ticket_work_and_land_finish.py test_tickets_organization.py test_tickets_priority.py unit/test_app_runners_batch6.py unit/test_app_runners_t2395_contention.py; T-2373 live-dirty test_ticket_new_priority_inherit_t1960.py test_waive_audit_runner.py verify/test_backpressure.py (checked its worktree git status fresh, genuinely dirty right now); T-2806 tests/unit/test_check.py