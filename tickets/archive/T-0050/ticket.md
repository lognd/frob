---
id: T-0050
title: 'strata phase 1: surface language v0 + std.trust + refinement'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0049
parent: T-0047
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/unit/strata/**
- design/litmus/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens::test_golden_1_third_party_response_reaches_ledger_unendorsed
- tests/unit/strata/test_litmus_surface.py::TestHardenedSurfaceGoldens::test_every_assert_holds_after_the_remedies
designated_repro_test: null
acceptance:
- text: GIVEN design/litmus/payments.strata WHEN frob sys check runs THEN it parses,
    elaborates, and reproduces the phase-0 golden findings via CI
  evidence: []
threat: null
component: null
---
Recursive-descent parser (pydantic AST, typani Result diagnostics), elaborator framework (vocabularies desugar to kernel facts, prover never learns domain terms), std.trust, assert/assume with owner+expiry, refine blocks with faithfulness checks. See docs/strata/surface.md.