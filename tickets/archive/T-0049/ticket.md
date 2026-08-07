---
id: T-0049
title: 'strata phase 0: kernel + prover core'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0048
parent: T-0047
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_litmus_payments.py::TestGoldenFindings::test_golden_1_third_party_response_reaches_ledger_unendorsed
- tests/unit/strata/test_litmus_payments.py::TestGoldenFindings::test_golden_2_refund_decision_reads_a_stale_replica
designated_repro_test: null
acceptance:
- text: GIVEN hand-written kernel facts for the payments litmus WHEN the prover runs
    THEN all golden findings fire with path counterexamples and quantifier-tagged
    verdicts
  evidence: []
threat: null
component: null
---
Kernel data model + fact base + closure + claim evaluation. Pure Python first; hot kernels move to strata-core (PyO3) later. See docs/strata/kernel.md.