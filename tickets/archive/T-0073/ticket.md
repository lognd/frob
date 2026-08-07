---
id: T-0073
title: 'strata scenario engine: node loss, rate surge, trust downgrade'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0051
parent: T-0052
tier: ticket
sprint: null
scope:
- strata-core/**
- docs/strata/**
- tickets.md
- src/frob/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_scenarios.py::TestEvaluateScenarios::test_remove_node_cascades_to_flows_and_boundaries
- tests/unit/strata/test_scenarios.py::TestEvaluateScenarios::test_scale_rate_fails_closed_on_unrated_flow
- tests/unit/strata/test_scenarios.py::TestElaborateScenario::test_fails_closed_on_unknown_trust_level
designated_repro_test: null
threat: null
component: null
---
Scenario = counterfactual model rewrite; all claims re-checked under it; quorum/placement arithmetic; retry-storm multipliers.