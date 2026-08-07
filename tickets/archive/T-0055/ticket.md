---
id: T-0055
title: 'strata kernel data model: Node/Flow/Boundary/Bound/Claim/Scenario'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0048
parent: T-0049
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/unit/strata/**
- docs/strata/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_models.py::TestLattice::test_leq_is_reflexive_transitive_and_ordered
- tests/unit/strata/test_models.py::TestQuantity::test_leq_across_dimensions_is_an_error_not_false
- tests/unit/strata/test_models.py::TestKernelModel::test_frozen_models_compare_by_value
designated_repro_test: null
threat: null
component: null
---
Frozen pydantic models for the 6 primitives; flows carry payload label, rate, size, age and may be conditioned on phase/outcome (on Ok / on Err / in parse). Law 1: every surface construct must desugar to these.