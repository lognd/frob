---
id: T-0191
title: wire DUP001/DUP002 smart-dup rules into frob check gates -- pipeline currently
  inert
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: T-0187
tier: ticket
sprint: null
scope:
- tickets.md
- src/frob/gates/**
- src/frob/dup/**
- frob.toml
- tests/**
- docs/modules/dup.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestOptInGates::test_dup_gate_fires_on_planted_clone_when_enabled
- tests/test_gates.py::TestOptInGates::test_dup_gate_planted_clone_waived_passes
designated_repro_test: null
threat: null
component: null
---
Survey finding (dup-sota-survey.md sec 0/3.1): DUP001/DUP002 are pure rule functions never invoked from frob.gates.__init__; frob check still runs only the legacy Type-1/2 scanner, so the whole R1-R5 smart pipeline never gates a build. Wire the clones gate to the smart pipeline behind the existing opt-in leaf, fixture tests proving a planted R3/R4 clone fails check when enabled and passes when waived. Highest priority of the T-0187 tree: everything else is inert until this lands.