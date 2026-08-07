---
id: T-0352
title: 'structural PII/secrets: TS/Rust field-shape equivalents'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/lang/**
- tests/test_gates.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0352 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/gates.md
  reason: T-0352 gates work maps to docs/modules/gates.md
  actor: logan
  at: '2026-07-20'
evidence:
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_interface_email_field_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_type_alias_password_field_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_class_field_token_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_clean_interface_is_silent
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_index_signature_reported_not_skipped
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_process_env_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_process_env_subscript_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_import_meta_env_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_dynamic_env_key_still_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_allowlisted_env_var_is_silent
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_struct_ssn_field_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_clean_struct_is_silent
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_env_var_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_unqualified_env_var_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_allowlisted_env_var_is_silent
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_tuple_struct_field_not_matched
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_and_rust_findings_joined_against_declared_surface
designated_repro_test: null
threat: null
component: null
---
T-0207 follow-on: frob.gates._pii_structural.FIELD_SIGNATURES is Python-only (ast-based). Extend PII010/SEC110 to TypeScript/Rust field-shape and env-access equivalents (process.env, std::env::var) per the ticket body's cross-language mandate. Deferred from T-0207's scope.