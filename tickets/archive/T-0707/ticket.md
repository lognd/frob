---
id: T-0707
title: 'selfconform: SYS102 unmodeled code src/frob/registry -- model the registry
  package'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- design/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
designated_repro_test: null
acceptance:
- text: GIVEN the strata selfconform gate WHEN it runs on this repo THEN TestRealGateGreen
    passes with src/frob/registry bound to a node
  evidence: []
threat: null
component: null
---
The long-standing known failure tests/unit/strata/test_selfconform.py::TestRealGateGreen: src/frob/registry (the T-0407 unified registry package) has no strata node binding -- SYS102 unmodeled-code fires on frob's own model. Every agent this session re-confirmed it as pre-existing; no ticket tracked it until now. Bind the registry package into the .strata model with its real interface/purpose/effects.