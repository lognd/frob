---
id: T-1283
title: 'TEST005 burn-down: src/frob/cycle (7 findings, 5 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/cycle/**
- tests/cycle/**
- tests/unit/test_cycle.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_cycle.py
  reason: existing test file convention is tests/unit/test_cycle.py, not tests/cycle/
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/test_cycle.py::test_cross_edge_to_finished_component_does_not_affect_lowlink
designated_repro_test: null
acceptance:
- text: GIVEN the cycle package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/cycle/**
  evidence:
  - tests/unit/test_cycle.py::test_cross_edge_to_finished_component_does_not_affect_lowlink
- text: GIVEN a 0.0%-branch symbol in cycle WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/test_cycle.py::test_cross_edge_to_finished_component_does_not_affect_lowlink
- text: GIVEN a new test added to close a cycle TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/test_cycle.py::test_cross_edge_to_finished_component_does_not_affect_lowlink
threat: null
component: null
---
Package: src/frob/cycle (or the listed root modules).
TEST005 findings at current baseline: 7 total, 5 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
graph.py :: DependencyGraph.add_edge
graph.py :: DependencyGraph.add_node
graph.py :: DependencyGraph.nodes
graph.py :: DependencyGraph.neighbors
graph.py :: find_cycles

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.