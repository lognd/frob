---
id: T-0058
title: strata payments litmus as kernel facts + golden findings
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0057
parent: T-0049
tier: ticket
sprint: null
scope:
- docs/strata/**
- tickets.md
- tests/unit/strata/**
- design/litmus/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_litmus_payments.py::TestGoldenFindings::test_golden_1_third_party_response_reaches_ledger_unendorsed
- tests/unit/strata/test_litmus_payments.py::TestGoldenFindings::test_golden_2_refund_decision_reads_a_stale_replica
- tests/unit/strata/test_litmus_payments.py::TestGoldenFindings::test_golden_3_at_least_once_webhook_into_non_idempotent_consumer
- tests/unit/strata/test_litmus_payments.py::TestHardenedModel::test_every_assert_holds_after_the_remedies
designated_repro_test: null
threat: null
component: null
---
Hand-written kernel facts for the Stripe-shaped model; goldens: foreign-response endorsement gap, stale-replica refund path, webhook idempotency. Phase-0 exit criterion.