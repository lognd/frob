---
id: T-0233
title: broken frob:doc target suppresses other coverage findings on the same file
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov001_broken_doc_edge_does_not_suppress_finding
- tests/test_gates.py::TestCoverageGate::test_cov001_passes_when_documented
- tests/test_gates.py::test_gates_run_gates_integration
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 21 (correctness): feldspar had DOC002 anchor-less targets; fixing them UNMASKED 6 previously-unreported COV001s on the same files -- a broken doc edge was counting as coverage. A frob:doc edge that fails to resolve must not satisfy COV001. Regression: fixture with a broken edge asserts COV001 still fires.