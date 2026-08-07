---
id: T-0042
title: 'TEST007: pair-level integration obligations from uses-contract edges'
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/test_gates.py
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestPairLevelIntegration::test_test007_fires_on_uncovered_boundary
- tests/test_gates.py::TestPairLevelIntegration::test_test007_passes_when_boundary_tested
designated_repro_test: null
threat: null
component: null
---
