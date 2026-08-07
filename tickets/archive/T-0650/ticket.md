---
id: T-0650
title: 'strata: transactional-boundary obligation on multi-write ops'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0649
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
- tests/unit/strata/test_txn.py::TestMissingTxnBoundary::test_multi_store_write_op_without_boundary_fires
- tests/unit/strata/test_txn.py::TestMissingTxnBoundary::test_single_store_write_op_clean
- tests/unit/strata/test_txn.py::TestMissingTxnBoundary::test_transaction_attr_discharges
- tests/unit/strata/test_txn.py::TestMissingTxnBoundary::test_saga_attr_discharges
- tests/unit/strata/test_txn.py::TestMissingTxnBoundary::test_empty_store_ids_emits_nothing
- tests/unit/strata/test_txn.py::TestMissingTxnBoundary::test_waiver_discharges_finding
- tests/unit/strata/test_txn.py::TestUnprovenTxnBoundary::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_txn.py::TestUnprovenTxnBoundary::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_txn.py::TestUnprovenTxnBoundary::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
designated_repro_test: null
acceptance:
- text: Given a multi-write op with no transactional-boundary declared, when checked,
    then the obligation fires
  evidence:
  - tests/unit/strata/test_txn.py::TestMissingTxnBoundary::test_multi_store_write_op_without_boundary_fires
threat: null
component: null
---
Any op writing to >1 store must declare a transactional boundary (or saga, see distributed-txn ticket). Reuses the store-writer graph built for the single-source-of-truth obligation.