---
id: T-0430
title: extend PII010 FIELD_SIGNATURES toward GDPR/CCPA/HIPAA/PCI-DSS/NIST-800-122
  field-name coverage parity
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_pii_structural.py
- tests/test_pii_structural_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[account_number]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[drivers_license]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[license_number]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[vehicle_id]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[vin]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[imei]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[mac_address]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[device_serial]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[medical_record_number]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[beneficiary_id]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[maiden_name]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[geolocation]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[ethnicity]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[political_affiliation]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[religion]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[union_membership]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[sexual_orientation]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[genetic_data]
- tests/test_pii_structural_gate.py::TestFieldNames::test_password_field_fires
designated_repro_test: null
threat: null
component: null
---
Found while dispositioning docs/design/registry/pii.yaml (T-0343 drain batch 1). PII010 structural FIELD_SIGNATURES covers a genuine subset of the PII field-name corpus; 6 pii.yaml entries deferred here for the coverage gap (GDPR/CCPA/HIPAA/PCI-DSS/NIST-800-122 field-name categories not yet in FIELD_SIGNATURES). Extend the signatures toward parity with fixtures, or narrow the corpus rows on review. (Ticket id reconciled from drainer draft T-draft-d77facd9; secrets sibling is T-0427.)