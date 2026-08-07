---
id: T-0084
title: 'strata frob sys plan: obligation -> ticket compiler'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0053
parent: T-0054
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/tickets/**
- src/frob/app/**
- src/frob/__main__.py
- src/frob/gates/__init__.py
- tests/**
- docs/commands/**
- docs/index.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_plan.py::TestPlanObligations::test_unrefined_frontier
- tests/unit/strata/test_plan.py::TestPlanObligations::test_refuted_claim
- tests/unit/strata/test_plan.py::TestPlanObligations::test_clean_model_plans_nothing
- tests/unit/strata/test_plan.py::TestPlanObligations::test_unbound_boundary
- tests/unit/strata/test_plan.py::TestPlanObligations::test_idempotent_markers
- tests/unit/strata/test_plan.py::TestClaimEvaluationSanity::test_refuted_model_actually_refutes
- tests/system/test_cli_sys_plan.py::TestSysPlanCli::test_dry_run_prints_tree_without_writing
- tests/system/test_cli_sys_plan.py::TestSysPlanCli::test_apply_writes_ticket_tree
- tests/system/test_cli_sys_plan.py::TestSysPlanCli::test_second_apply_is_a_noop
- tests/unit/strata/test_plan.py::TestPlanObligations::test_threat_frontier
- tests/unit/strata/test_design_load.py::TestUnbound::test_unbound_pair
- tests/unit/strata/test_design_load.py::TestUnbound::test_bound_excluded
- tests/system/test_cli_sys_plan.py::TestSysPlanCli::test_dropped_ticket_is_not_recreated
designated_repro_test: null
threat: null
component: null
---
REFUTED claims, undischarged obligations, expiring assumes become scoped tickets (scope from counterexample paths, blocked_by from proof dependencies, STRIDE prefilled); idempotent re-planning; sys tickets close only when the claim discharges at the required rung.