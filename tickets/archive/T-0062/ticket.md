---
id: T-0062
title: 'strata refinement: abstract components, refine blocks, faithfulness'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0049
parent: T-0050
tier: ticket
sprint: null
scope:
- strata-core/**
- Makefile
- .github/**
- docs/strata/**
- tickets.md
- src/frob/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_refine.py::TestRefineHappyPath::test_flattens_abstract_node_and_rewires_outer_flow
- tests/unit/strata/test_refine.py::TestRefineHappyPath::test_noflow_claim_proved_at_abstract_level_stays_proved_after_refinement
- tests/unit/strata/test_refine.py::TestRefineViolations::test_foreign_inner_node_under_trusted_abstract_fails_trust_laundering
- tests/unit/strata/test_refine.py::TestUnrefinedFrontier::test_unrefined_abstract_node_keeps_marker
designated_repro_test: null
threat: null
component: null
---
Three faithfulness checks: no new external surface, no trust laundering, budget distribution. Policies inherit downward monotonically; code binding legal only on leaves.