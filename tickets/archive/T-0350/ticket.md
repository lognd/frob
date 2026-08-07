---
id: T-0350
title: 'structural PII/secrets: keyword-sweep suggestion severity (family 5)'
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
- tests/test_gates.py
- docs/modules/gates.md
- tests/test_pii_structural_gate.py
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
  reason: T-0350 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/gates.md
  reason: T-0350 gates work maps to docs/modules/gates.md
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_pii_structural_gate.py
  reason: T-0455 scope hygiene narrowed tests/** to tests/test_gates.py, the wrong
    mirrored path -- this family's actual test file (used as T-0207 predecessor's
    evidence) is tests/test_pii_structural_gate.py
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_identifier_keyword_fires_at_suggestion_severity
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_function_parameter_keyword_fires
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_comment_keyword_fires
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_unrelated_identifier_does_not_fire
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_tokenizer_identifier_does_not_falsely_match_token
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_data_structure_field_not_double_reported
designated_repro_test: null
threat: null
component: null
---
T-0207 follow-on: identifier/comment keyword hits at suggestion severity only (no hard fail on names alone), reusing frob.gates._pii_structural.FIELD_SIGNATURES. Deferred from T-0207's scope.