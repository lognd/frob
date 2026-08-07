---
id: T-1300
title: 'TEST005 burn-down: src/frob/registry (11 findings, 0 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/registry/**
- tests/registry/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_registry_models.py::TestLoadRegistryDir::test_loads_typed_entries
- tests/test_registry_staleness.py::TestReg010Gate::test_missing_gate_rule_entry_warns
- tests/test_capability_registry.py::TestNegativeFixtures::test_re_compile_is_not_eval
designated_repro_test: null
acceptance:
- text: GIVEN the registry package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/registry/**
  evidence:
  - tests/test_registry_models.py::TestLoadRegistryDir::test_loads_typed_entries
  - tests/test_registry_staleness.py::TestReg010Gate::test_missing_gate_rule_entry_warns
  - tests/test_capability_registry.py::TestNegativeFixtures::test_re_compile_is_not_eval
- text: GIVEN a 0.0%-branch symbol in registry WHEN it is judged dead code THEN it
    is routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/test_registry_models.py::TestLoadRegistryDir::test_loads_typed_entries
- text: GIVEN a new test added to close a registry TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/test_registry_models.py::TestLoadRegistryDir::test_loads_typed_entries
  - tests/test_registry_staleness.py::TestReg010Gate::test_missing_gate_rule_entry_warns
  - tests/test_capability_registry.py::TestNegativeFixtures::test_re_compile_is_not_eval
threat: null
component: null
---
Package: src/frob/registry (or the listed root modules).
TEST005 findings at current baseline: 11 total, 0 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
(none at exactly 0.0% -- all findings are partial-coverage or module-line)

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.