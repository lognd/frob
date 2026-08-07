---
id: T-0649
title: 'strata: SINGLE SOURCE OF TRUTH obligation - two nodes writing one store is
  a hazard'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
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
- tests/unit/strata/test_ssot.py::TestMissingOwner::test_multi_writer_store_without_owner_fires
- tests/unit/strata/test_ssot.py::TestMissingOwner::test_single_writer_store_clean
- tests/unit/strata/test_ssot.py::TestMissingOwner::test_owner_attr_discharges
- tests/unit/strata/test_ssot.py::TestMissingOwner::test_reconciliation_attr_discharges
- tests/unit/strata/test_ssot.py::TestMissingOwner::test_empty_store_ids_emits_nothing
- tests/unit/strata/test_ssot.py::TestMissingOwner::test_waiver_discharges_finding
- tests/unit/strata/test_ssot.py::TestUnprovenOwner::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_ssot.py::TestUnprovenOwner::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_ssot.py::TestUnprovenOwner::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
designated_repro_test: null
acceptance:
- text: Given a store with >=2 distinct writer nodes and no declared single-owner/reconciliation,
    when checked, then the obligation fires
  evidence:
  - tests/unit/strata/test_ssot.py::TestMissingOwner::test_multi_writer_store_without_owner_fires
threat: null
component: null
---
Extends SYS003 hub: a store written by two or more distinct nodes without a declared owner/reconciliation is a hard obligation failure.