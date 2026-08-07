---
id: T-0762
title: 'structural PII type-kind: TS/Rust nominal PII-shaped types (branded email,
  secrecy::Secret/SecretString wrappers)'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0352
tier: ticket
sprint: null
scope:
- src/frob/gates/_pii_structural.py
- tests/test_gates.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_secret_wrapper_type_field_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_branded_email_type_field_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_plain_string_field_type_does_not_fire
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_secrecy_secretstring_type_field_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_secret_newtype_type_field_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_plain_string_field_type_does_not_fire
designated_repro_test: null
acceptance:
- text: GIVEN a TS field typed as a known secret-wrapper or a Rust field typed secrecy::SecretString
    WHEN pii_structural runs THEN a type-kind PII finding fires; a plain String field
    does not
  evidence:
  - tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_secret_wrapper_type_field_fires
  - tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_branded_email_type_field_fires
  - tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_plain_string_field_type_does_not_fire
  - tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_secrecy_secretstring_type_field_fires
  - tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_secret_newtype_type_field_fires
  - tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_plain_string_field_type_does_not_fire
threat: null
component: null
---
From T-0352 (TS/Rust structural PII, landed): the NAME-kind field detection is cross-language, but TYPE-kind PII signals (Python EmailStr/SecretStr) stay Python-only. Extend to nominal PII-shaped TYPES in TS/Rust: TS branded/nominal email types and known secret-wrapper types; Rust secret-wrapper crate types (secrecy::Secret, SecretString) and newtype PII wrappers. Requires resolving a field/binding TYPE to a known-PII-type registry per language -- coordinate with T-0717 capability taxonomy and the T-0611/T-0612 adapters type info. Disclosed in T-0352 module docstring, not silently dropped.