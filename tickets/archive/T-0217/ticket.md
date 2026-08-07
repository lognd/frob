---
id: T-0217
title: sys plan/doc log raw pre-discharge threat counts that contradict the PROVED
  verdict
state: done
kind: ux
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/app/sys_runner.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_threat.py::TestEvaluateThreats::test_pre_discharge_count_log_is_honest_and_debug_level
- tests/system/test_cli_sys_plan.py::TestSysPlanCli::test_threat_pre_discharge_count_never_reads_as_contradicting_output
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (gap 13): 'threat: evaluated ... -> 13 violation(s)' logs right before '0 obligation tickets / PROVED' -- the 13 is the pre-discharge obligation count, not live violations. Rename the log line (obligations evaluated, N discharged, 0 residual) or demote to DEBUG; contradictory-looking output erodes trust in PROVED.