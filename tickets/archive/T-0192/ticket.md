---
id: T-0192
title: frob dup --probe CLI flag reaching probe_equivalence (R6) -- closes T-0041
  debt
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: T-0187
tier: ticket
sprint: null
scope:
- tickets.md
- src/frob/dup/**
- src/frob/app/**
- src/frob/__main__.py
- tests/**
- docs/modules/dup.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup_rungs.py::test_cli_probe_equivalent_functions
designated_repro_test: null
threat: null
component: null
---
R6 probe_equivalence is fully implemented and unreachable (no --probe string anywhere under the CLI, confirmed by survey). Wire the flag, document the workload contract, CLI-level test.