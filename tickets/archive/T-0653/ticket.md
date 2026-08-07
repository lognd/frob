---
id: T-0653
title: 'strata: retention/TTL obligation on PII stores'
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
- tests/unit/strata/test_pii.py::TestPiiRetentionErasure::test_pii_with_no_retention_or_erasure_fires_pii003
- tests/unit/strata/test_pii.py::TestPiiRetentionErasure::test_declared_retention_discharges
- tests/unit/strata/test_pii.py::TestPiiRetentionErasure::test_revocation_edge_discharges
- tests/unit/strata/test_pii.py::TestPiiRetentionErasure::test_no_pii_no_finding
designated_repro_test: null
acceptance:
- text: Given a PII-tagged store with no retention/TTL declared, when checked, then
    the obligation fires
  evidence:
  - tests/unit/strata/test_pii.py::TestPiiRetentionErasure::test_pii_with_no_retention_or_erasure_fires_pii003
  - tests/unit/strata/test_pii.py::TestPiiRetentionErasure::test_declared_retention_discharges
  - tests/unit/strata/test_pii.py::TestPiiRetentionErasure::test_revocation_edge_discharges
  - tests/unit/strata/test_pii.py::TestPiiRetentionErasure::test_no_pii_no_finding
threat: null
component: null
---
Every store holding PII must declare a retention/TTL policy (ties T-0207).