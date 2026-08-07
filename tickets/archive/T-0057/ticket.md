---
id: T-0057
title: 'strata claim evaluation: noflow/bound/reach with counterexample traces'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0056
parent: T-0049
tier: ticket
sprint: null
scope:
- docs/strata/**
- tickets.md
- src/frob/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_claims.py::TestNoFlow::test_refuted_with_witness_path_when_no_boundary_intervenes
- tests/unit/strata/test_claims.py::TestReach::test_refutation_of_exists_is_a_forall
- tests/unit/strata/test_claims.py::TestBounds::test_age_bound_refuted_with_stalest_path_and_number
designated_repro_test: null
threat: null
component: null
---
Verdicts PROVED/EVIDENCED/ASSUMED/REFUTED, quantifier-tagged (forall/exists); every REFUTED carries a path or a number, never a vibe. Interval arithmetic for bounds; z3 only for nonlinear.