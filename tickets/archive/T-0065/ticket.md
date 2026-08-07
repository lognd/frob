---
id: T-0065
title: strata age/staleness propagation (TTL = rotation = RPO = expiry)
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0050
parent: T-0051
tier: ticket
sprint: null
scope:
- docs/strata/**
- tickets.md
- strata-core/**
- Makefile
- .github/**
- design/litmus/**
- src/frob/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_kernel_properties.py::test_reachable_matches_bfs_oracle
- tests/unit/strata/test_kernel_properties.py::test_worst_age_matches_longest_path_oracle_on_dags
- tests/unit/strata/test_kernel_properties.py::test_worst_age_cycle_property
- tests/unit/strata/test_kernel_properties.py::test_demand_matches_sum_oracle
- tests/unit/strata/test_kernel_properties.py::test_reachable_is_deterministic
- tests/unit/strata/test_kernel_properties.py::test_worst_age_is_deterministic
- tests/unit/strata/test_kernel_properties.py::test_demand_is_deterministic
- tests/unit/strata/test_kernel_properties.py::TestReviewerRegression::test_context_dependent_memo_undercount
- tests/unit/strata/test_kernel_properties.py::TestReviewerRegression::test_adversarial_shared_node_divergent_entry_a
- tests/unit/strata/test_kernel_properties.py::TestReviewerRegression::test_adversarial_shared_node_divergent_entry_b
- tests/unit/strata/test_kernel_properties.py::TestReviewerRegression::test_adversarial_three_way_convergence
- tests/unit/strata/test_facts.py::TestBuildFacts::test_negative_age_fails_closed
- tests/unit/strata/test_facts.py::TestBuildFacts::test_negative_rate_fails_closed
- tests/unit/strata/test_facts.py::TestBuildFacts::test_nonnegative_age_is_accepted
designated_repro_test: null
threat: null
component: null
---
One age metric propagated along read paths; freshness requirements proved or refuted with the accumulating path.