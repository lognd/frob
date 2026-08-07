---
id: T-0069
title: strata six-phase boundaries + outcome-conditioned frames
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
- tests/unit/strata/test_boundary_phases.py::TestPhaseBlockHappyPath::test_effect_and_record_phases_generate_flows
- tests/unit/strata/test_boundary_phases.py::TestOperationFailClosed::test_cross_store_atomic_via_without_coordinator_is_refused
- tests/unit/strata/test_observe.py::TestEndToEnd::test_phases_operation_and_observe_together
designated_repro_test: null
threat: null
component: null
---
admit/parse/judge/effect/record/refuse with per-phase frames and label rules; no-effects-before-judgment; refusal frame is audit-only; error responses are labeled egress flows; modifies-on-Ok/Err claims.