---
id: T-0063
title: strata payments litmus in surface syntax + CI goldens
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0049
parent: T-0050
tier: ticket
sprint: null
scope:
- strata-core/**
- Makefile
- .github/**
- docs/strata/**
- tickets.md
- design/litmus/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens::test_golden_1_third_party_response_reaches_ledger_unendorsed
- tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens::test_golden_2_refund_decision_reads_a_stale_replica
- tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens::test_render_report_shows_refuted_before_proved_with_the_witness_path
- tests/unit/strata/test_litmus_surface.py::TestHardenedSurfaceGoldens::test_every_assert_holds_after_the_remedies
designated_repro_test: null
threat: null
component: null
---
design/litmus/payments.strata reproduces phase-0 findings end to end through parser+elaborator; goldens wired into CI. Phase-1 exit criterion.