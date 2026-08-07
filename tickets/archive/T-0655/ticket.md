---
id: T-0655
title: 'strata: distributed-transaction-across-services requires saga/compensation'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0650
parent: T-0331
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_distributed_txn.py::TestMissingSaga::test_multi_service_write_op_without_saga_fires
- tests/unit/strata/test_distributed_txn.py::TestMissingSaga::test_transaction_attr_alone_does_not_discharge
- tests/unit/strata/test_distributed_txn.py::TestMissingSaga::test_single_write_and_discharged_clean
- tests/unit/strata/test_distributed_txn.py::TestMissingSaga::test_waiver_discharges_finding
- tests/unit/strata/test_distributed_txn.py::TestUnprovenSaga::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_distributed_txn.py::TestUnprovenSaga::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_distributed_txn.py::TestUnprovenSaga::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
designated_repro_test: null
acceptance:
- text: Given a cross-service transaction with no saga/compensation declared, when
    checked, then the obligation fires
  evidence:
  - tests/unit/strata/test_distributed_txn.py::TestMissingSaga::test_multi_service_write_op_without_saga_fires
  - tests/unit/strata/test_distributed_txn.py::TestMissingSaga::test_transaction_attr_alone_does_not_discharge
  - tests/unit/strata/test_distributed_txn.py::TestMissingSaga::test_single_write_and_discharged_clean
  - tests/unit/strata/test_distributed_txn.py::TestMissingSaga::test_waiver_discharges_finding
  - tests/unit/strata/test_distributed_txn.py::TestUnprovenSaga::test_declared_with_no_code_evidence_fires
  - tests/unit/strata/test_distributed_txn.py::TestUnprovenSaga::test_declared_with_real_code_evidence_discharges
  - tests/unit/strata/test_distributed_txn.py::TestUnprovenSaga::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
threat: null
component: null
---
A transaction spanning multiple services must declare a saga/compensation strategy; builds on the transactional-boundary obligation's multi-write detection extended across service boundaries.