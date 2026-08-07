---
id: T-0038
title: 'ADR decision records: frob:decision edges + DEC gates'
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
- src/frob/graph/**
- tests/test_decisions.py
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_decisions.py::test_dec002_accepted_decision_unanchored
- tests/test_decisions.py::test_dec001_dangling_decision_edge
designated_repro_test: null
threat: null
component: null
---
